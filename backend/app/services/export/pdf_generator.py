"""Generate a polished PDF from an already-persisted final summary."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any
import time

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


class SummarySourceNotFoundError(FileNotFoundError):
    """Raised when no persisted final summary can be used."""


_PRIMARY = colors.HexColor("#176B68")
_DARK = colors.HexColor("#17324D")
_MUTED = colors.HexColor("#627386")
_LINE = colors.HexColor("#D8E2E8")


def _register_fonts() -> tuple[str, str]:
    """Use ReportLab's bundled Unicode font when available."""
    import reportlab

    fonts_directory = Path(reportlab.__file__).resolve().parent / "fonts"
    regular_path = fonts_directory / "Vera.ttf"
    bold_path = fonts_directory / "VeraBd.ttf"
    if regular_path.is_file() and bold_path.is_file():
        if "SummaryVera" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("SummaryVera", regular_path))
            pdfmetrics.registerFont(TTFont("SummaryVera-Bold", bold_path))
        return "SummaryVera", "SummaryVera-Bold"
    return "Helvetica", "Helvetica-Bold"


def _load_persisted_summary(json_path: Path, markdown_path: Path) -> str:
    """Prefer final Markdown persisted in JSON, with the Markdown file as fallback."""
    if json_path.is_file():
        try:
            with json_path.open("r", encoding="utf-8") as handle:
                payload: Any = json.load(handle)
            if isinstance(payload, dict):
                markdown = payload.get("summary_markdown")
                if isinstance(markdown, str) and markdown.strip():
                    return markdown.strip()
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass

    if markdown_path.is_file():
        try:
            markdown = markdown_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            markdown = ""
        if markdown:
            return markdown

    raise SummarySourceNotFoundError("Persisted final summary not found")


def _inline_markup(text: str) -> str:
    """Convert the small inline-Markdown subset emitted by the summary prompt."""
    safe_text = escape(text.strip())
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe_text)
    safe_text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", safe_text)
    return safe_text


def _document_styles() -> dict[str, ParagraphStyle]:
    regular_font, bold_font = _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SummaryTitle",
            parent=base["Title"],
            fontName=bold_font,
            fontSize=23,
            leading=29,
            textColor=_DARK,
            alignment=TA_CENTER,
            spaceAfter=10 * mm,
        ),
        "heading": ParagraphStyle(
            "SummaryHeading",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=14,
            leading=18,
            textColor=_PRIMARY,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "subheading": ParagraphStyle(
            "SummarySubheading",
            parent=base["Heading3"],
            fontName=bold_font,
            fontSize=11.5,
            leading=15,
            textColor=_DARK,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "SummaryBody",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#263746"),
            alignment=TA_LEFT,
            spaceAfter=2.5 * mm,
        ),
        "bullet": ParagraphStyle(
            "SummaryBullet",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=9.5,
            leading=14,
            leftIndent=7 * mm,
            firstLineIndent=-4 * mm,
            bulletIndent=1 * mm,
            textColor=colors.HexColor("#263746"),
            spaceAfter=1.5 * mm,
        ),
    }


def _markdown_story(markdown: str) -> list[Any]:
    styles = _document_styles()
    story: list[Any] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            content = "<br/>".join(_inline_markup(line) for line in paragraph_lines)
            story.append(Paragraph(content, styles["body"]))
            paragraph_lines.clear()

    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue
        if re.fullmatch(r"-{3,}", line):
            flush_paragraph()
            story.extend(
                [Spacer(1, 1.5 * mm), HRFlowable(width="100%", thickness=0.6, color=_LINE)]
            )
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            content = _inline_markup(heading.group(2))
            if level == 1:
                if story:
                    story.append(PageBreak())
                story.append(Paragraph(content, styles["title"]))
            else:
                style = styles["heading"] if level == 2 else styles["subheading"]
                story.append(Paragraph(content, style))
            continue

        bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$", line)
        if bullet:
            flush_paragraph()
            story.append(
                Paragraph(_inline_markup(bullet.group(1)), styles["bullet"], bulletText="•")
            )
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    return story


def _draw_page(canvas: Any, document: Any) -> None:
    """Add a restrained running header, footer, and page number."""
    canvas.saveState()
    width, height = A4
    regular_font, bold_font = _register_fonts()
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, height - 15 * mm, width - 20 * mm, height - 15 * mm)
    canvas.setFont(bold_font, 7.5)
    canvas.setFillColor(_PRIMARY)
    canvas.drawString(20 * mm, height - 11.5 * mm, "YONNOVIA")
    canvas.setFont(regular_font, 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawRightString(width - 20 * mm, 11 * mm, f"{document.page}")
    canvas.line(20 * mm, 15 * mm, width - 20 * mm, 15 * mm)
    canvas.restoreState()


def generate_summary_pdf(
    *,
    json_path: Path,
    markdown_path: Path,
    output_path: Path,
) -> Path:
    """Render persisted summary artifacts to a PDF without invoking the pipeline."""
    markdown = _load_persisted_summary(json_path, markdown_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=23 * mm,
        bottomMargin=22 * mm,
        title="Scientific Summary",
        author="YONNOVIA",
    )
    story = _markdown_story(markdown)
    if not story:
        raise SummarySourceNotFoundError("Persisted final summary is empty")
    start_time = time.perf_counter()

    document.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    pdf_export_time = time.perf_counter() - start_time
    print(
         f"Timing | PDF Export | "
    f"{pdf_export_time:.3f} seconds"
    )



    return output_path
