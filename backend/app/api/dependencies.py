from typing import Generator
from sqlalchemy.orm import Session
from app.models.database import get_db


def get_database() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes
    
    Yields:
        SQLAlchemy database session
    """
    yield from get_db()
