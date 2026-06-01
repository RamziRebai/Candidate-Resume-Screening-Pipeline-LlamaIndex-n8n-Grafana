# Services Runtime

This folder contains background execution services that connect API sessions to the workflow engine.

## File

- `workflow_runtime.py`: main runtime service for executing workflows, handling feedback loops, parsing results, and post-processing outputs

## Responsibilities

- Build dynamic workflow config from API request
- Run `IntelligentResumeMatchingWorkflow` asynchronously
- Stream and persist workflow events/logs to session state
- Detect and handle human-in-the-loop checkpoints (`InputRequiredEvent`)
- Continue execution after user feedback (`HumanResponseEvent`)
- Normalize output fields for frontend consumption
- Generate PDF and optionally upload to Google Drive

## Integration Points

- Workflow package: `workflow/`
- Session manager: `app/session.py`
- FastAPI routes: `app/routers/sessions.py`
- External services: Playwright, Google Drive API

## Operational Caveats

- Session state is in-memory; process restarts clear active sessions.
- Long-running tasks execute in FastAPI background task context.
- Google Drive upload depends on OAuth credential files and runtime authorization.
