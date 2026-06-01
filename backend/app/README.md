# App Package

The `app` package contains the FastAPI application layer: app wiring, request models, session state management, API routing, and runtime orchestration hooks.

## Responsibilities

- Build and configure FastAPI app instance
- Register middleware and routers
- Define request/response models with validation
- Manage in-memory workflow sessions and WebSocket connections
- Delegate heavy execution to service layer

## Key Files

- `main_app.py`: FastAPI app initialization and router registration
- `models.py`: Pydantic models for config, feedback, and results
- `session.py`: Session manager and WebSocket log transport
- `core/`: startup/shutdown lifecycle logic
- `routers/`: REST and WebSocket endpoints
- `services/`: long-running workflow execution and feedback continuation

## Design Notes

- This package intentionally separates HTTP transport concerns from workflow engine internals.
- Business/workflow code lives in `workflow/` and is consumed via service functions.
- Session storage is currently in memory and suitable for single-node runtime.

## Related Docs

- [core/README.md](core/README.md)
- [routers/README.md](routers/README.md)
- [services/README.md](services/README.md)
- [../README.md](../README.md)
