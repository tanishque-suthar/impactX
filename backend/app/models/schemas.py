from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnalyzeRequest(BaseModel):
    """Request model for repository analysis"""
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field(None, description="Branch to analyze (defaults to default branch)")


class JobStatus(BaseModel):
    """Response model for job status"""
    job_id: int
    repo_url: str
    status: str  # pending, processing, completed, failed
    progress_detail: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VulnerabilityItem(BaseModel):
    """Individual vulnerability in health report"""
    severity: str  # critical, high, medium, low
    description: str
    affected_component: Optional[str] = None
    recommendation: Optional[str] = None


class TechDebtItem(BaseModel):
    """Technical debt item in health report"""
    category: str  # code_smell, duplication, complexity, etc.
    description: str
    file_path: Optional[str] = None
    priority: Optional[str] = None


class ModernizationSuggestion(BaseModel):
    """Modernization suggestion in health report"""
    type: str  # dependency_upgrade, refactoring, containerization, etc.
    description: str
    rationale: Optional[str] = None
    effort_estimate: Optional[str] = None


class HealthReportData(BaseModel):
    """Structure of the health report JSON"""
    code_quality_score: float = Field(..., ge=0, le=100, description="Overall code quality score (0-100)")
    vulnerabilities: List[VulnerabilityItem] = []
    tech_debt_items: List[TechDebtItem] = []
    modernization_suggestions: List[ModernizationSuggestion] = []
    overall_summary: str
    
    # Additional metadata
    languages_detected: Optional[Dict[str, int]] = None  # {language: file_count}
    dependencies_found: Optional[Dict[str, List[str]]] = None  # {ecosystem: [packages]}
    total_files_analyzed: Optional[int] = None
    analysis_timestamp: Optional[datetime] = None


class HealthReportResponse(BaseModel):
    """Response model for health report"""
    job_id: int
    report: HealthReportData
    created_at: datetime
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
