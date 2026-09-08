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
3. Create a PostgreSQL credential and select it in `Store Session Data - Execute Query`, `Store Field Analytics`, `Store Feedback Analytics`, and `Store Confidence Scores`.
4. Create a Slack credential, then select it and your destination channel in `Send Critical Alert v3.0`.
5. Ensure the `rag_analytics` database schema and tables from `../sql_queries/` exist.
6. Activate the workflow and copy its production webhook URL into the backend `N8N_WEBHOOK_URL` setting.

The public export intentionally contains no credential IDs, account names, Slack channel, workflow ID, n8n instance ID, or tag IDs. It is inactive on import so credentials must be configured before execution.

## Note

Folder name is intentionally kept as `n8n_worflow` to preserve project compatibility.
