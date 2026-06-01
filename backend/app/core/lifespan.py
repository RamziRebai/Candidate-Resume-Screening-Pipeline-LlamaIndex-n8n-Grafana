import asyncio
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger(__name__)

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
def _check_playwright_browsers() -> bool:
    """Return True if Playwright chromium can launch, False otherwise."""
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); b = p.chromium.launch(); "
             "b.close(); p.stop(); print('ok')"],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False

PLAYWRIGHT_AVAILABLE: bool = _check_playwright_browsers()

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Resume Matching System API")
    
    # Create uploads directory
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # Playwright browser check
    if PLAYWRIGHT_AVAILABLE:
        logger.info("✅ Playwright Chromium browser: available")
    else:
        logger.warning(
            "⚠️  Playwright Chromium browser NOT found!  "
            "PDF generation will fall back to xhtml2pdf (lower quality).  "
            "Run 'playwright install chromium' to fix this."
        )
    
    logger.info("API server started successfully")
    
    yield
    
    # Shutdown (if needed)
    logger.info("Shutting down AI Resume Matching System API")

