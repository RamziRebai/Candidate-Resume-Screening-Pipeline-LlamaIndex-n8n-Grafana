# n8n Workflow Template

This folder contains the canonical n8n workflow export used as an importable automation template.

## File

- `n8n_workflow.json`: full webhook-driven workflow definition for report ingestion, analytics processing, persistence, alerting, and response handling

## Key Behaviors In Template

- Receives workflow reports via webhook path `rag-report-processor`
- Processes confidence and performance analytics
- Executes PostgreSQL insert queries for session and field analytics
- Routes alert notifications (critical/warning)
- Builds structured response payload for upstream caller

## How To Use

1. Open n8n.
2. Import `n8n_workflow.json`.
3. Configure credentials (PostgreSQL, Slack, and other integrations).
4. Verify webhook URL matches backend `N8N_WEBHOOK_URL`.
5. Activate workflow.

## Note

Folder name is intentionally kept as `n8n_worflow` to preserve project compatibility.
