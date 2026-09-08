# YONNOVIA Scientific PDF Summarization Backend

This project extracts and preprocesses scientific PDFs, prepares section-level
prompts, runs a configurable inference engine, and produces a final scientific
summary through FastAPI. The original Jupyter notebook remains a demonstration
client, while migrated business logic lives in the backend service layer.

## Architecture

```text
FastAPI routes / demonstration notebook
                    |
                    v
             DocumentPipeline
                    |
     validation -> extraction -> quality evaluation
                    |
     cleaning -> metadata -> sections -> keywords -> chunking
                    |
     prompt preparation -> InferenceFactory
                              |       |
                              v       v
                         Ollama   vLLM placeholder
                              |
                              v
                   partial-summary generation
                              |
                              v
                  multilingual final summary
```

The merge stage uses the language detected during preprocessing: English
documents produce English summaries and French documents produce French
summaries. It does not translate source content.

## Folder structure

```text
backend/
|-- app/
|   |-- api/
|   |   `-- routes/             # /health, /upload, /summarize
|   |-- core/                   # Environment-backed configuration and folders
|   |-- models/                 # Pydantic request and response models
|   |-- services/
|   |   |-- extraction/
|   |   |-- preprocessing/
|   |   |-- prompting/
|   |   |-- inference/
|   |   |-- summarization/
|   |   |-- pipeline/           # DocumentPipeline orchestration
|   |   `-- evaluation/
|   `-- utils/
|-- .env.example
|-- requirements.txt
`-- run.py
```

Runtime uploads are stored in `UPLOAD_DIR`. Generated artifacts are isolated by
document name under `OUTPUT_DIR`:

```text
outputs/<document_name>/
|-- extraction/
|   |-- markdown.md
|   `-- extraction_report.json
|-- preprocessing/
|   |-- cleaned_text.txt
|   |-- metadata.json
|   |-- sections.json
|   |-- keywords.json
|   `-- chunks.json
|-- prompting/
|   `-- inference_requests.json
|-- inference/
|   `-- partial_summaries.json
`-- summary/
    |-- summary.md
    `-- summary.json
```

Application timing and error logs are written to `OUTPUT_DIR/logs/app.log`.
Existing artifacts for the same document name are replaced on a subsequent
successful run.

## Installation

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment, then install runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

Install Ollama separately and pull the configured model:

```bash
ollama pull qwen2.5vl:7b
```

The metadata service can use spaCy for author recognition when spaCy and the
`en_core_news_sm` or `fr_core_news_sm` model are installed. This support is
optional; the backend remains operational without it.

## Environment variables

Copy `.env.example` to `.env` and adjust values as needed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `PDF Summarization Backend` | OpenAPI application title |
| `APP_VERSION` | `0.1.0` | OpenAPI application version |
| `API_HOST` | `0.0.0.0` | Uvicorn bind address |
| `API_PORT` | `8000` | Uvicorn port |
| `API_RELOAD` | `true` | Development reload mode |
| `CORS_ORIGINS` | Localhost ports 5173 and 8080 | Comma-separated frontend origins allowed by CORS |
| `UPLOAD_DIR` | `uploads` | PDF upload directory, relative to `backend/` unless absolute |
| `OUTPUT_DIR` | `outputs` | Pipeline output directory, relative to `backend/` unless absolute |
| `BACKEND_ENGINE` | `ollama` | Inference engine selected by `InferenceFactory` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen2.5vl:7b` | Ollama model name |
| `OLLAMA_TEMPERATURE` | `0.2` | Generation temperature |
| `OLLAMA_TOP_P` | `0.9` | Nucleus-sampling parameter |
| `OLLAMA_NUM_PREDICT` | `1200` | Maximum generated tokens, sized for the complete final-summary structure |
| `OLLAMA_NUM_CTX` | `4096` | Ollama context size |
| `OLLAMA_QUALITY_NUM_CTX` | `8192` | Context size for visual extraction-quality evaluation |

Environment variables override `.env`; `.env` values override built-in defaults.

## Run FastAPI

From `backend/`:

```bash
python run.py
```

Alternatively:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Available endpoints:

- `GET /health`
- `POST /upload`
- `POST /summarize`
- `GET /summary/{filename}`
- `GET /summary/{filename}/markdown`
- `GET /summary/{filename}/json`
- API documentation at `/docs`

Upload a PDF first, then pass its filename to `/summarize`:

```json
{
  "filename": "paper.pdf",
  "model": null
}
```

## Run the notebook

Open `Pipeline_IA_Extraction_Resume_PDF.ipynb` from the repository root or in
Google Colab. Keep the `backend/` directory beside the notebook so its startup
cell can add the backend package to `sys.path`. Run cells from top to bottom.

The notebook retains explanatory Markdown, uploads, artifact inspection, and
demonstration output. Migrated stages import backend services instead of defining
duplicate implementations. Ollama must already be installed and running before
cells that perform model-backed quality evaluation or inference.

## Future vLLM switch

`VLLMEngine` already implements the common `BaseInferenceEngine` interface as a
documented placeholder. To enable vLLM later:

1. Implement `VLLMEngine.generate(request)` without changing callers.
2. Add the required vLLM runtime dependency.
3. Set `BACKEND_ENGINE=vllm` in `.env`.

`DocumentPipeline`, prompt generation, partial-summary generation, routes, and
the notebook require no architectural changes for that switch.
