from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import init_db
from app.api.routes import router
from app.utils.logger import logger


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
    
    yield
    
    # Shutdown
    logger.info("Shutting down Phoenix Agent API...")


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
        "api_keys_configured": len(settings.GOOGLE_API_KEYS)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
