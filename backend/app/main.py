from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.core.logging_utils import configure_logging
from app.database import init_db
from app.api import scans, websocket, schedules, system

# Configure structured JSON logging (idempotent).
configure_logging(level=settings.log_level, include_uvicorn=True)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Network Scanner API",
    description="Advanced network scanning tool with FastAPI backend",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scans.router)
app.include_router(websocket.router)
app.include_router(schedules.router)
app.include_router(system.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the failure and return a generic message (no internals leaked)."""
    logger.error(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Network Scanner API...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Display disclaimer
    logger.info("=" * 80)
    logger.info("LEGAL DISCLAIMER")
    logger.info("=" * 80)
    logger.info("This network scanning tool is intended for use on LOCAL NETWORKS ONLY.")
    logger.info("Scanning networks without proper authorization is illegal.")
    logger.info("Use this tool responsibly and only on networks you own or have")
    logger.info("explicit permission to scan.")
    logger.info("=" * 80)

    if settings.env.lower() == "production" and settings.uses_default_secret:
        logger.warning(
            "SECRET_KEY is still the placeholder value; set a strong secret "
            "before exposing the API."
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Network Scanner API...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Network Scanner API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/api/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
