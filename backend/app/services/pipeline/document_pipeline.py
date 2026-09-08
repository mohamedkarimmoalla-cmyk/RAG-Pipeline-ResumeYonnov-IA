"""Orchestrator for the PDF summarization pipeline."""

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional
import re
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    ExtractionResult,
    InferenceRun,
    PipelineRun,
    PreprocessingResult,
    Summary,
)
from app.core.config import OUTPUT_DIR, UPLOAD_DIR
from app.core.constants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RUNNING
from app.services.extraction.extractor import (
    evaluate_extraction_quality,
    extract_pdf_content,
    validate_pdf_extension,
    validate_pdf_readable,
)
from app.services.inference.factory import InferenceFactory
from app.services.inference.ollama_engine import OLLAMA_CONFIG
from app.services.preprocessing.chunking import chunk_document
from app.services.preprocessing.cleaning import clean_extracted_text
from app.services.preprocessing.keywords import extract_article_keywords
from app.services.preprocessing.metadata import extract_article_metadata
from app.services.preprocessing.pipeline import (
    remove_excluded_sections,
    select_relevant_sections,
)
from app.services.preprocessing.sections import detect_sections
from app.services.prompting.builder import build_shared_prefix
from app.services.prompting.requests import build_inference_requests
from app.services.summarization.merge_summary import merge_summary, parse_summary_to_json
from app.services.summarization.partial_summary import generate_partial_summaries
from app.utils.file_utils import ensure_parent_directory
from app.utils.json_utils import write_json
from app.utils.logger import logger
from app.services.summarization.extractive_fallback import (
    generate_extractive_final_summary,
)
from app.services.quality.judge import SummaryQualityJudge

class DocumentPipeline:
    """Coordinate the notebook-compatible PDF summarization workflow."""

    def __init__(self, upload_dir: Optional[Path] = None, output_dir: Optional[Path] = None, db: Optional[Session] = None,) -> None:
        self.upload_dir = upload_dir or UPLOAD_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        self.db = db

    def _resolve_pdf_path(self, pdf_path: str | Path) -> Path:
        """Resolve API filenames inside the configured upload directory."""
        resolved_path = Path(pdf_path)
        if not resolved_path.is_absolute():
            resolved_path = self.upload_dir / resolved_path.name
        return resolved_path

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        """Persist text with the notebook's UTF-8 encoding behavior."""
        ensure_parent_directory(path).write_text(content, encoding="utf-8")

    @staticmethod
    def _log_timing(stage: str, started_at: float) -> None:
        """Log one completed pipeline stage duration."""
        logger.info("Timing | %s | %.3f seconds", stage, perf_counter() - started_at)

    def run(self, pdf_path: str | Path, document_id: UUID,model: Optional[str] = None) -> Dict[str, Any]:
        """Run the existing services in notebook execution order."""
        total_started_at = perf_counter()
        stage = "validation"
        pipeline_run = None
        logger.info("Starting pipeline for document_id=%s", document_id)

        try:
            resolved_pdf_path = self._resolve_pdf_path(pdf_path)

            if not validate_pdf_extension(resolved_pdf_path):
                raise ValueError("Only PDF files are supported")

            if not validate_pdf_readable(resolved_pdf_path):
                raise ValueError("PDF file is not readable")

            if self.db is not None:
                pipeline_run = PipelineRun(
                    document_id=document_id,
                    status=STATUS_RUNNING,
                    model=model,
                )
                self.db.add(pipeline_run)
                self.db.commit()
            document_output_dir = self.output_dir / resolved_pdf_path.stem

            stage = "extraction"
            stage_started_at = perf_counter()
            markdown_path = document_output_dir / "extraction" / "markdown.md"
            pages, extracted_markdown, extraction_report = extract_pdf_content(
                resolved_pdf_path,
                resolved_pdf_path.name,
                markdown_path,
            )
            self._write_text(markdown_path, extracted_markdown)
            write_json(
                document_output_dir / "extraction" / "extraction_report.json",
                extraction_report,
            )
            self._log_timing("Extraction", stage_started_at)

            stage = "quality"
            stage_started_at = perf_counter()
            extraction_quality = evaluate_extraction_quality(resolved_pdf_path, pages)
            if pipeline_run is not None and self.db is not None:
                extraction_result = ExtractionResult(
                    pipeline_run_id=pipeline_run.id,
                    extraction_method=extraction_report.get(
                        "Extraction Method",
                        "unknown",
                    ),
                    quality_score=extraction_quality.get("average_score"),
                    decision=extraction_quality.get("decision"),
                    page_count=extraction_report.get("Pages"),
                    extraction_report={
                        "extraction": extraction_report,
                        "quality": extraction_quality,
                        },
                    )
                self.db.add(extraction_result)
                self.db.flush()

                





            self._log_timing("Quality Evaluation", stage_started_at)

            stage = "preprocessing/cleaning"
            stage_started_at = perf_counter()
            cleaned_text, page_tagged_lines, cleaning_report = clean_extracted_text(
                extracted_markdown,
                min_repeat_ratio=0.6,
            )
            cleaned_path = document_output_dir / "preprocessing" / "cleaned_text.txt"
            self._write_text(cleaned_path, cleaned_text)
            self._log_timing("Cleaning", stage_started_at)

            stage = "preprocessing/metadata"
            stage_started_at = perf_counter()
            metadata = extract_article_metadata(
                cleaned_text,
                pdf_path=str(resolved_pdf_path),
            )
            metadata_path = document_output_dir / "preprocessing" / "metadata.json"
            write_json(metadata_path, metadata)
            self._log_timing("Metadata", stage_started_at)

            stage = "preprocessing/sections"
            stage_started_at = perf_counter()
            sections, missing_sections = detect_sections(page_tagged_lines)
            sections_path = document_output_dir / "preprocessing" / "sections.json"
            write_json(sections_path, sections)
            self._log_timing("Sections", stage_started_at)

            stage = "preprocessing/keywords"
            stage_started_at = perf_counter()
            keywords = extract_article_keywords(
                cleaned_text,
                language=metadata.get("language", "en"),
                top_n=15,
                keywords_per_section=5,
            )
            keywords_path = document_output_dir / "preprocessing" / "keywords.json"
            write_json(keywords_path, keywords)
            self._log_timing("Keywords", stage_started_at)

            stage = "preprocessing/chunking"
            stage_started_at = perf_counter()
            selected_sections = select_relevant_sections(sections)
            filtered_sections = remove_excluded_sections(selected_sections)
            chunked_sections = chunk_document(filtered_sections)
            print("\n" + "=" * 60)
            print("CHUNK DETAILS")
            print("=" * 60)
            print(f"Total chunks: {len(chunked_sections)}")

            for chunk in chunked_sections:
                content = str(chunk.get("content", ""))
                word_count = len(content.split())

                print(
                f"Chunk {chunk.get('chunk_id')} | "
                f"Section: {chunk.get('section_name')} | "
                f"Words: {word_count}"
                )

                print("=" * 60)

            write_json(
                document_output_dir / "preprocessing" / "chunks.json",
                chunked_sections,
            )
            self._log_timing("Chunking", stage_started_at)
            if pipeline_run is not None and self.db is not None:
                preprocessing_result = PreprocessingResult(
                    pipeline_run_id=pipeline_run.id,
                    article_metadata=metadata,
                    article_keywords=keywords,
                    sections=sections,
                    missing_sections=missing_sections,
                    selected_sections=selected_sections,
                    filtered_sections=filtered_sections,
                    chunked_sections=chunked_sections,
                    cleaning_report=cleaning_report,
                )
                self.db.add(preprocessing_result)
                self.db.flush()

            stage = "prompting"
            stage_started_at = perf_counter()
            shared_prefix = build_shared_prefix(metadata, keywords)
            inference_requests = build_inference_requests(
                chunked_sections,
                shared_prefix,
            )
            inference_requests_path = (
                document_output_dir / "prompting" / "inference_requests.json"
            )
            write_json(inference_requests_path, inference_requests)
            self._log_timing("Prompting", stage_started_at)

            stage = "inference"
            stage_started_at = perf_counter()

            inference_config = OLLAMA_CONFIG.copy()
            if model:
                inference_config["model"] = model

            effective_model = inference_config.get("model")
            if pipeline_run is not None and effective_model:
                pipeline_run.model = effective_model

            engine = InferenceFactory.create_engine(config=inference_config)

            inference_run = None

            if pipeline_run is not None and self.db is not None:
                inference_run = InferenceRun(
                    pipeline_run_id=pipeline_run.id,
                    model=inference_config.get("model"),
                    status=STATUS_RUNNING,
                    request_count=len(inference_requests),
                    completed_count=0,
                    failed_count=0,
                    inference_config=inference_config,
                )

                self.db.add(inference_run)
                self.db.flush()

            try:
                partial_summaries = generate_partial_summaries(
                inference_requests,
                engine,
                keywords,
                )

                completed_count = sum(
                    1
                    for item in partial_summaries
                    if item.get("status") != "fallback"
                )

                failed_count = sum(
                    1
                    for item in partial_summaries
                    if item.get("status") == "fallback"
                )

                if inference_run is not None:
                    inference_run.status = STATUS_COMPLETED
                    inference_run.completed_count = completed_count
                    inference_run.failed_count = failed_count
                    inference_run.completed_at = datetime.now(timezone.utc)
                    inference_run.duration_ms = (
                        perf_counter() - stage_started_at
                    ) * 1000

                    inference_run.result_metadata = {
                        "total_results": len(partial_summaries),
                        "fallback_count": failed_count,
                    }

                    self.db.flush()

            except Exception as exc:
                if inference_run is not None and self.db is not None:
                    inference_run.status = STATUS_FAILED
                    inference_run.completed_at = datetime.now(timezone.utc)
                    inference_run.duration_ms = (
                        perf_counter() - stage_started_at
                    ) * 1000
                    inference_run.error_message = str(exc)

                    self.db.flush()

                raise

            partial_summaries_path = (
                document_output_dir / "inference" / "partial_summaries.json"
            )

            write_json(partial_summaries_path, partial_summaries)
            self._log_timing("Inference", stage_started_at)

            stage = "merge"
            stage_started_at = perf_counter()
            final_merge_used_fallback = False
            try:
                summary_markdown = merge_summary(
                    metadata,
                    keywords,
                    partial_summaries,
                    engine,
            )
            except Exception as exc:
                logger.warning(
                    "LLM final merge failed: %s. Using extractive fallback.",
                    exc,
                )
                final_merge_used_fallback = True

                summary_markdown = generate_extractive_final_summary(
                    metadata,
                    keywords,
                    partial_summaries,
                )
            summary_structured = parse_summary_to_json(
                summary=summary_markdown,
                metadata=metadata,
                keywords=keywords,
            )
            
            source_sections = {}
            for section in sections:
                section_name = section.get("section_name")
                content = section.get("content")
                if section_name and content:
                    source_sections[section_name] = content
            source_for_judge = {
                "metadata": metadata,
                "keywords": keywords,
                "sections": source_sections,
            }
            import json

            logger.info(
                "JUDGE SOURCE SIZE | metadata=%d | keywords=%d | sections=%d | total=%d",
                len(json.dumps(metadata, ensure_ascii=False)),
                len(json.dumps(keywords, ensure_ascii=False)),
                len(json.dumps(source_sections, ensure_ascii=False)),
                len(json.dumps(source_for_judge, ensure_ascii=False)),
            )
            logger.info(
                 "JUDGE PAYLOAD | source=%d | summary=%d | total=%d",
    len(json.dumps(source_for_judge, ensure_ascii=False)),
    len(json.dumps(summary_structured, ensure_ascii=False)),
    len(json.dumps(source_for_judge, ensure_ascii=False))
    + len(json.dumps(summary_structured, ensure_ascii=False)),
)


            if final_merge_used_fallback:
                logger.info(
                     "Skipping LLM quality evaluation because the final "
        "summary was generated using extractive fallback."
    )
                quality_report = None
                quality_evaluation = "SKIPPED_FALLBACK"
            else:
                judge = SummaryQualityJudge()
                quality_report = judge.evaluate(
                    source=source_for_judge,
                    summary=summary_structured,
                )
                quality_evaluation="LLM"


            logger.info(
                "JUDGE SOURCE KEYS: %s",
                source_for_judge.keys(),
            )

            summary_markdown_path = document_output_dir / "summary" / "summary.md"
            markdown_export_started_at = perf_counter()

            self._write_text(summary_markdown_path, summary_markdown)
            markdown_export_time = perf_counter() - markdown_export_started_at
            print(
                f"Timing | Markdown Export | "
                f"{markdown_export_time:.3f} seconds"
            )
            quality_report_path = (
                document_output_dir / "summary" / "quality_report.json"
            )
            if quality_report is not None:
                write_json(quality_report_path, quality_report)

            engine_config = getattr(engine, "config", {}) or {}
            summary_payload = {
                "filename": resolved_pdf_path.name,
                "metadata": metadata,
                "summary": summary_structured,
                "summary_markdown": summary_markdown,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": engine_config.get("model", "Non disponible"),
                "quality_report": quality_report,
                "quality_evaluation": quality_evaluation,
            }
            summary_json_path = document_output_dir / "summary" / "summary.json"


            write_json(
                summary_json_path,
                summary_payload,

                
            )
            if pipeline_run is not None and self.db is not None:
                summary_record = Summary(
                    pipeline_run_id=pipeline_run.id,
                    summary_text=summary_markdown,
                    summary_json=summary_payload,

                
                )
                self.db.add(summary_record)
                self.db.flush()





            self._log_timing("Merge", stage_started_at)
            if pipeline_run is not None:
                pipeline_run.status = STATUS_COMPLETED
                pipeline_run.completed_at = datetime.now(timezone.utc)
                pipeline_run.duration_ms = (
                    perf_counter() - total_started_at
                ) * 1000

                self.db.commit()

            return {
                "status": STATUS_COMPLETED,
                "message": "Pipeline completed",
                "pdf_path": str(resolved_pdf_path),
                "summary_path": str(summary_markdown_path),
                "pages": pages,
                "extracted_markdown": extracted_markdown,
                "cleaned_text": cleaned_text,
                "metadata": metadata,
                "extraction_report": extraction_report,
                "extraction_quality": extraction_quality,
                "cleaning_report": cleaning_report,
                "sections": sections,
                "missing_sections": missing_sections,
                "keywords": keywords,
                "selected_sections": selected_sections,
                "filtered_sections": filtered_sections,
                "chunked_sections": chunked_sections,
                "inference_requests": inference_requests,
                "partial_summaries": partial_summaries,
                "quality_report": quality_report,
            }
        
        
        except Exception as exc:  # pragma: no cover - error boundary
            logger.exception(
                "Pipeline failed at stage=%s for document_id=%s",
                stage,
                document_id,
            )

            if pipeline_run is not None and self.db is not None:
                try:
                    pipeline_run.status = STATUS_FAILED
                    pipeline_run.completed_at = datetime.now(timezone.utc)
                    pipeline_run.duration_ms = (
                        perf_counter() - total_started_at
                    ) * 1000
                    pipeline_run.failure_stage = stage
                    pipeline_run.error_message = str(exc)

                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    logger.exception("Failed to persist pipeline failure state.")


                    

        
            return {
                "status": STATUS_FAILED,
                "message": f"{stage} failed: {exc}",
                "pdf_path": str(pdf_path),
                "failure_stage": stage,
            }
