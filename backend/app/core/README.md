# Core Lifecycle

This folder contains application lifecycle primitives used by FastAPI startup and shutdown.

## Contents

- `lifespan.py`: lifecycle context manager, runtime boot checks, upload directory bootstrap

## What Happens On Startup

- Applies Windows-compatible asyncio policy when needed
- Ensures `uploads/` directory exists
- Checks whether Playwright Chromium is available
- Logs readiness state and warning fallback when browser binaries are missing

## Why It Matters

- Keeps startup concerns isolated from API route logic
- Prevents missing runtime directories in production
- Makes PDF generation capability explicit at boot time

## Operational Notes

If Playwright browser is missing, PDF generation can fall back to lower-quality alternatives where implemented. Install browser binaries with:

```bash
playwright install chromium
```
