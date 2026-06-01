# API Routers

This folder exposes HTTP and WebSocket interfaces for session orchestration and n8n integration diagnostics.

## Files

- `sessions.py`: main workflow session API + WebSocket log stream
- `n8n.py`: n8n connection and test-report utility endpoints

## Session Router Highlights

- Create session with runtime workflow configuration
- Upload resume and application form files
- Start asynchronous workflow processing
- Retrieve status, logs, debug, and final results
- Submit human feedback for iterative refinement
- Stream live events through `/ws/{session_id}`

## n8n Router Highlights

- Validate n8n webhook connectivity
- Send synthetic test report payloads
- Expose active webhook configuration metadata

## API Stability

- Endpoints are organized by function and can be versioned later under shared prefixes.
- Route handlers are intentionally lightweight and delegate long-running logic to `app/services`.
