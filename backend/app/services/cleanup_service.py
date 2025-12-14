"""
Cleanup service for managing repository retention policy.
Automatically deletes old cloned repositories based on retention settings.
"""

import os
import shutil
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.models.database import AnalysisJob, get_db
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
settings = Settings()


class CleanupService:
    """Service for cleaning up old repositories based on retention policy"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.temp_repos_dir = Path("temp_repos")
    
    def start(self):
        """Start the cleanup scheduler"""
        # Run cleanup every CLEANUP_CHECK_INTERVAL_SECONDS
        self.scheduler.add_job(
            self.cleanup_old_repositories,
            "interval",
            seconds=settings.CLEANUP_CHECK_INTERVAL_SECONDS,
            id="cleanup_old_repos",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(
            f"Cleanup scheduler started: checking every {settings.CLEANUP_CHECK_INTERVAL_SECONDS}s, "
            f"retention period: {settings.REPO_RETENTION_MINUTES} minutes"
        )
    
    def stop(self):
        """Stop the cleanup scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Cleanup scheduler stopped")
    
    async def cleanup_old_repositories(self):
        """
        Clean up repositories older than REPO_RETENTION_MINUTES.
        Deletes both the temp directory and optionally the database records.
        """
        try:
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(minutes=settings.REPO_RETENTION_MINUTES)
            
            logger.info(f"Running cleanup check (cutoff: {cutoff_time.isoformat()})")
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                # Query jobs older than retention period with completed/failed status
                old_jobs = db.query(AnalysisJob).filter(
                    AnalysisJob.created_at < cutoff_time,
                    AnalysisJob.status.in_(["completed", "failed"])
                ).all()
                
                deleted_count = 0
                failed_count = 0
                
                for job in old_jobs:
                    job_dir = self.temp_repos_dir / str(job.id)
                    
                    if job_dir.exists():
                        try:
                            self._delete_directory(job_dir)
                            deleted_count += 1
                            logger.info(
                                f"Deleted old repository: job_id={job.id}, "
                                f"age={(datetime.utcnow() - job.created_at).total_seconds() / 60:.1f} minutes"
                            )
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"Failed to delete repository for job {job.id}: {e}")
                
                if deleted_count > 0 or failed_count > 0:
                    logger.info(
                        f"Cleanup completed: {deleted_count} deleted, {failed_count} failed"
                    )
                
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _delete_directory(self, path: Path):
        """
        Delete a directory and all its contents.
        Handles Windows readonly files (e.g., .git directory).
        """
        def handle_remove_readonly(func, path, exc):
            """Error handler for Windows readonly files"""
            os.chmod(path, stat.S_IWRITE)
            func(path)
        
        if path.exists():
            shutil.rmtree(path, onerror=handle_remove_readonly)
    
    def manual_cleanup(self, job_id: int, db: Session) -> bool:
        """
        Manually clean up a specific job's repository.
        Returns True if successful, False otherwise.
        """
        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            
            if not job:
                logger.warning(f"Job {job_id} not found for manual cleanup")
                return False
            
            job_dir = self.temp_repos_dir / str(job_id)
            
            if job_dir.exists():
                self._delete_directory(job_dir)
                logger.info(f"Manually deleted repository for job {job_id}")
                return True
            else:
                logger.info(f"Repository for job {job_id} does not exist (already cleaned?)")
                return True
        
        except Exception as e:
            logger.error(f"Failed to manually cleanup job {job_id}: {e}")
            return False
    
    def get_cleanup_stats(self, db: Session) -> dict:
        """
        Get statistics about repositories and cleanup status.
        """
        try:
            total_jobs = db.query(AnalysisJob).count()
            completed_jobs = db.query(AnalysisJob).filter(
                AnalysisJob.status == "completed"
            ).count()
            
            # Count existing repo directories
            existing_repos = 0
            total_size_mb = 0
            
            if self.temp_repos_dir.exists():
                for job_dir in self.temp_repos_dir.iterdir():
                    if job_dir.is_dir():
                        existing_repos += 1
                        # Calculate directory size
                        total_size_mb += sum(
                            f.stat().st_size for f in job_dir.rglob('*') if f.is_file()
                        ) / (1024 * 1024)
            
            # Calculate jobs eligible for cleanup
            cutoff_time = datetime.utcnow() - timedelta(minutes=settings.REPO_RETENTION_MINUTES)
            eligible_for_cleanup = db.query(AnalysisJob).filter(
                AnalysisJob.created_at < cutoff_time,
                AnalysisJob.status.in_(["completed", "failed"])
            ).count()
            
            return {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "existing_repositories": existing_repos,
                "total_size_mb": round(total_size_mb, 2),
                "eligible_for_cleanup": eligible_for_cleanup,
                "retention_minutes": settings.REPO_RETENTION_MINUTES,
                "next_cleanup_in_seconds": settings.CLEANUP_CHECK_INTERVAL_SECONDS
            }
        
        except Exception as e:
            logger.error(f"Failed to get cleanup stats: {e}")
            return {
                "error": str(e)
            }


# Global instance
cleanup_service = CleanupService()
