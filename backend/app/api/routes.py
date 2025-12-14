import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.api.dependencies import get_database
from app.models.database import AnalysisJob, HealthReport
from app.models.schemas import (
    AnalyzeRequest,
    JobStatus,
    HealthReportResponse,
    HealthReportData,
    ErrorResponse
)
from app.services.github_service import GitHubService
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.utils.logger import logger


router = APIRouter(prefix="/api", tags=["analysis"])

# Service instances
github_service = GitHubService()
rag_service = RAGService()
llm_service = LLMService()

# Simple lock to prevent concurrent jobs (MVP single-threading)
job_lock = {"is_running": False}


def update_job_status(db: Session, job_id: int, status: str, progress_detail: Optional[str] = None, error_message: Optional[str] = None):
    """Update job status in database"""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if job:
        job.status = status
        if progress_detail:
            job.progress_detail = progress_detail
        if error_message:
            job.error_message = error_message
        job.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Job {job_id} status updated: {status} - {progress_detail}")


def analyze_repository_background(job_id: int, repo_url: str, branch: Optional[str] = None):
    """
    Background task for repository analysis
    
    Args:
        job_id: Analysis job ID
        repo_url: Repository URL
        branch: Optional branch name
    """
    from app.models.database import SessionLocal
    
    db = SessionLocal()
    collection_name = None
    
    try:
        logger.info(f"Starting analysis for job {job_id}: {repo_url}")
        
        # Update status: Cloning
        update_job_status(db, job_id, "processing", "Cloning repository")
        
        # Clone and analyze repository
        files_data, languages, dependencies = github_service.analyze_repository(
            repo_url, job_id, branch
        )
        
        # Update status: Parsing
        update_job_status(db, job_id, "processing", f"Parsing files ({len(files_data)} found)")
        
        if not files_data:
            update_job_status(
                db, job_id, "failed",
                error_message="No valid text files found in repository"
            )
            return
        
        # Update status: Embedding
        def progress_callback(detail: str):
            update_job_status(db, job_id, "processing", detail)
        
        update_job_status(db, job_id, "processing", "Creating embeddings")
        
        collection_name = rag_service.create_embeddings(
            files_data=files_data,
            repo_url=repo_url,
            job_id=job_id,
            progress_callback=progress_callback
        )
        
        # Update status: Analyzing
        update_job_status(db, job_id, "processing", "Analyzing code with AI")
        
        # Get diverse, representative code samples (increased for better analysis)
        code_samples = rag_service.get_representative_samples(collection_name, max_samples=25)
        
        # Generate health report
        update_job_status(db, job_id, "processing", "Generating health report")
        
        health_report_data = llm_service.generate_health_report(
            languages=languages,
            dependencies=dependencies,
            total_files=len(files_data),
            code_samples=code_samples
        )
        
        # Save health report to database
        report_json = health_report_data.model_dump_json()
        
        health_report = HealthReport(
            job_id=job_id,
            report_json=report_json
        )
        db.add(health_report)
        db.commit()
        
        # Update status: Cleaning up
        update_job_status(db, job_id, "processing", "Cleaning up ChromaDB")
        
        # Only cleanup ChromaDB collection, keep repo for retention policy
        # github_service.cleanup_repository(job_id)  # Now handled by cleanup_service
        if collection_name:
            rag_service.delete_collection(collection_name)
        
        # Update status: Completed
        update_job_status(db, job_id, "completed", "Analysis completed successfully")
        
        logger.info(f"Successfully completed analysis for job {job_id}")
        
    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)
        
        # Cleanup on error
        try:
            github_service.cleanup_repository(job_id)
            if collection_name:
                rag_service.delete_collection(collection_name)
        except Exception as cleanup_error:
            logger.error(f"Cleanup failed: {cleanup_error}")
        
        # Update status: Failed
        update_job_status(
            db, job_id, "failed",
            error_message=str(e)
        )
    
    finally:
        job_lock["is_running"] = False
        db.close()


@router.post("/analyze", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database)
):
    """
    Initiate repository analysis
    
    Args:
        request: Analysis request with repo URL
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Job status
    """
    # Check if a job is already running (single-threaded for MVP)
    if job_lock["is_running"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Another analysis is already in progress. Please wait."
        )
    
    # Validate GitHub URL (basic validation)
    if "github.com" not in request.repo_url.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub repository URL"
        )
    
    # Create job record
    job = AnalysisJob(
        repo_url=request.repo_url,
        status="pending",
        progress_detail="Analysis queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(f"Created analysis job {job.id} for {request.repo_url}")
    
    # Set lock
    job_lock["is_running"] = True
    
    # Add background task
    background_tasks.add_task(
        analyze_repository_background,
        job_id=job.id,
        repo_url=request.repo_url,
        branch=request.branch
    )
    
    return JobStatus(
        job_id=job.id,
        repo_url=job.repo_url,
        status=job.status,
        progress_detail=job.progress_detail,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: int, db: Session = Depends(get_database)):
    """
    Get analysis job status
    
    Args:
        job_id: Job ID
        db: Database session
        
    Returns:
        Job status
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return JobStatus(
        job_id=job.id,
        repo_url=job.repo_url,
        status=job.status,
        progress_detail=job.progress_detail,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.get("/report/{job_id}", response_model=HealthReportResponse)
async def get_health_report(job_id: int, db: Session = Depends(get_database)):
    """
    Get health report for completed job
    
    Args:
        job_id: Job ID
        db: Database session
        
    Returns:
        Health report
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed yet. Current status: {job.status}"
        )
    
    report = db.query(HealthReport).filter(HealthReport.job_id == job_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for job {job_id}"
        )
    
    # Parse JSON report
    report_data = HealthReportData.model_validate_json(report.report_json)
    
    return HealthReportResponse(
        job_id=job.id,
        report=report_data,
        created_at=report.created_at
    )
