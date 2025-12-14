from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import init_db
from app.api.routes import router
from app.utils.logger import logger
from app.services.cleanup_service import cleanup_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Phoenix Agent API...")
    
    # Initialize database
    init_db(settings.DATABASE_URL)
    logger.info(f"Database initialized at {settings.DATABASE_URL}")
    
    # Log configuration
    logger.info(f"Loaded {len(settings.GOOGLE_API_KEYS)} Google API keys")
    logger.info(f"Allowed file extensions: {settings.ALLOWED_EXTENSIONS}")
    logger.info(f"ChromaDB persist directory: {settings.CHROMA_PERSIST_DIR}")
    
    # Start cleanup scheduler
    cleanup_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Phoenix Agent API...")
    cleanup_service.stop()


# Create FastAPI app
app = FastAPI(
    title="Phoenix Agent API",
    description="Autonomous AI DevOps tool for analyzing and modernizing legacy codebases",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Phoenix Agent API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "analyze": "/api/analyze",
            "status": "/api/status/{job_id}",
            "report": "/api/report/{job_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "api_keys_configured": len(settings.GOOGLE_API_KEYS),
        "cleanup_scheduler": "running" if cleanup_service.scheduler.running else "stopped",
        "retention_minutes": settings.REPO_RETENTION_MINUTES
    }


@app.get("/api/cleanup/stats")
async def get_cleanup_stats():
    """Get repository cleanup statistics"""
    from app.api.dependencies import get_database
    db = next(get_database())
    try:
        stats = cleanup_service.get_cleanup_stats(db)
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
