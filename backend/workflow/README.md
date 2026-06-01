# Workflow Engine

This package implements the resume matching intelligence pipeline using LlamaIndex Workflow primitives.

## Purpose

Transform resume + application form inputs into structured, confidence-scored field responses with optional human review and analytics export.

## Modules

- `engine.py`: core workflow graph and execution steps
- `config.py`: runtime configuration and provider/model settings
- `models_events.py`: event and data model definitions used by workflow steps
- `monitoring.py`: execution telemetry, metrics, report export, n8n reporting
- `n8n.py`: asynchronous n8n webhook client with retries and enrichment
- `utils.py`: text processing and helper utilities
- `__init__.py`: public exports for app/service imports

## Execution Flow (High Level)

1. Validate inputs and initialize components.
2. Parse resume with Llama Cloud / LlamaParse.
3. Build embeddings and index in Qdrant.
4. Parse application form fields and generate queries.
5. Retrieve relevant resume context per field.
6. Produce field responses + confidence signals.
7. Trigger human feedback cycle when required.
8. Finalize, export monitoring report, and notify n8n.

## Runtime Flexibility

- Model/provider selection is driven by config values.
- Supports OpenAI, Azure OpenAI, and Google Gemini style providers.
- Embedding dimensions are inferred from embedding model selection.

## Integration Contracts

- Consumed by `app/services/workflow_runtime.py`.
- Emits events consumed by session manager/WebSocket layer.
- Sends enriched monitoring payloads to n8n webhook endpoints.
