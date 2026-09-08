# AI Resume Matcher Backend

Production-ready backend for intelligent resume-to-application-form matching, human-in-the-loop validation, analytics reporting, and automated PDF publishing.

This service exposes a FastAPI API, runs a LlamaIndex workflow pipeline, stores semantic vectors in Qdrant, sends execution analytics to n8n, and can publish final PDF reports to Google Drive.

## Sommaire

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Workflow Lifecycle](#workflow-lifecycle)
- [API Surface](#api-surface)
- [Configuration](#configuration)
- [Local Setup](#local-setup)
- [Sub-Directories](#sub-directories)
- [Security Notes](#security-notes)

## Overview

Core responsibilities:

- Session-based resume processing (`create -> upload -> run -> review -> finalize`)
- Intelligent extraction and matching via LlamaIndex workflow events
- Confidence scoring and human feedback loop
- n8n webhook integration for analytics and downstream automation
- PDF generation and optional Google Drive upload
- Real-time progress logs over WebSocket

## Architecture

```text
Client (Frontend / API tests)
    |
    v
FastAPI (app/main_app.py)
    |
    +--> Routers (sessions, n8n)
    |
    +--> Services (workflow_runtime)
             |
             +--> Workflow Engine (workflow/engine.py)
             |      +--> LlamaParse (Llama Cloud parsing)
             |      +--> LLM + Embeddings (OpenAI/Azure/Google)
             |      +--> Qdrant vector search
             |
             +--> Monitoring + report export
             |      +--> n8n webhook
             |
             +--> PDF generation
                    +--> Google Drive upload (optional)
```

## Tech Stack

- API: FastAPI, Uvicorn, Pydantic
- Orchestration: LlamaIndex Workflow
- Parsing: LlamaParse / Llama Cloud (often referred to as LlamaIndex LiteParse pipeline)
- Retrieval: Qdrant + LlamaIndex vector store integration
- LLM providers: OpenAI, Azure OpenAI, Google Gemini (model-driven selection)
- Async HTTP: httpx
- Realtime: WebSockets
- Automation: n8n webhooks + workflow templates
- Reporting: Playwright (HTML -> PDF)
- Storage integration: Google Drive API (OAuth)

## Project Structure

```text
backend/
  app/                  # API application package (routers, core lifecycle, services)
  workflow/             # Workflow engine, config, monitoring, n8n client, events
  n8n_worflow/          # n8n import template (note folder spelling kept as-is)
  n8n_workflows/        # Generated workflow monitoring report snapshots
  sql_queries/          # PostgreSQL setup and analytics SQL scripts
  uploads/              # Runtime uploaded files and generated reports
  main.py               # Local entrypoint
  pyproject.toml        # Python project and dependencies (managed by uv)
  uv.lock               # Reproducible dependency lockfile
  SETUP_GOOGLE_DRIVE.md # Google Drive setup guide
```

## Workflow Lifecycle

1. Create session via `POST /api/sessions` with runtime config.
2. Upload resume and application form via `POST /api/sessions/{session_id}/upload`.
3. Start background workflow via `POST /api/sessions/{session_id}/start`.
4. Consume logs/status via REST and WebSocket (`/ws/{session_id}`).
5. If needed, submit feedback via `POST /api/sessions/{session_id}/feedback`.
6. Receive final fields via `GET /api/sessions/{session_id}/results`.
7. On completion, backend generates PDF and optionally uploads to Google Drive.

## API Surface

Primary endpoints:

- `POST /api/sessions`
- `POST /api/sessions/{session_id}/upload`
- `POST /api/sessions/{session_id}/start`
- `GET /api/sessions/{session_id}/status`
- `POST /api/sessions/{session_id}/feedback`
- `GET /api/sessions/{session_id}/results`
- `GET /api/sessions/{session_id}/debug`
- `GET /api/health`

n8n utility endpoints:

- `GET /api/n8n/test-connection`
- `POST /api/n8n/send-test-report`
- `GET /api/n8n/webhook-info`

## Configuration

Typical environment variables:

- `LLAMA_PARSE_API_KEY`
- `QDRANT_API_KEY`
- `QDRANT_CLUSTER_ENDPOINT`
- `GOOGLE_API_KEY`
- `AZURE_API_KEY`
- `AZURE_ENDPOINT`
- `AZURE_EMBED_API_KEY`
- `AZURE_EMBED_ENDPOINT`
- `N8N_WEBHOOK_URL`
- `N8N_WEBHOOK_TIMEOUT`
- `N8N_WEBHOOK_MAX_RETRIES`
- `N8N_WEBHOOK_ENABLED`
- `GOOGLE_DRIVE_FOLDER_ID` (optional)

## Local Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.
2. Create the virtual environment and install the locked dependencies:

```bash
uv sync
```

Add or remove dependencies with `uv add <package>` and `uv remove <package>`; both commands update `pyproject.toml` and `uv.lock`.

3. Install Playwright browser:

```bash
uv run playwright install chromium
```

4. Configure `.env` with required keys.
5. Run API:

```bash
uv run python main.py
```

Server defaults to `http://0.0.0.0:8000`.

## Sub-Directories

Detailed documentation and navigation links are available for each backend sub-directory:

- [app/README.md](app/README.md)
- [app/core/README.md](app/core/README.md)
- [app/routers/README.md](app/routers/README.md)
- [app/services/README.md](app/services/README.md)
- [workflow/README.md](workflow/README.md)
- [n8n_worflow/README.md](n8n_worflow/README.md)
- [n8n_workflows/README.md](n8n_workflows/README.md)
- [sql_queries/README.md](sql_queries/README.md)
- [uploads/README.md](uploads/README.md)

## Security Notes

Do not commit secrets or runtime private artifacts:

- Credentials and tokens (`*.json`, OAuth tokens, API keys)
- Uploaded files and generated reports containing personal data
- Local PDFs generated during processing

Before pushing to GitHub:

- Verify `.gitignore` coverage
- Rotate any key that was accidentally committed
- Clean sensitive sample data from `uploads/`
