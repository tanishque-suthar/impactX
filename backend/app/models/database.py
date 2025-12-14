from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class AnalysisJob(Base):
    """Represents a repository analysis job"""
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    progress_detail = Column(String, nullable=True)  # Granular progress updates
    error_message = Column(Text, nullable=True)  # Error details if failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to health report
    health_report = relationship("HealthReport", back_populates="job", uselist=False, cascade="all, delete-orphan")


class HealthReport(Base):
    """Stores the generated health report for a job"""
    __tablename__ = "health_reports"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("analysis_jobs.id"), unique=True, nullable=False)
    report_json = Column(Text, nullable=False)  # JSON blob of the health report
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to job
    job = relationship("AnalysisJob", back_populates="health_report")


# Database engine and session
engine = None
SessionLocal = None


def init_db(database_url: str):
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
