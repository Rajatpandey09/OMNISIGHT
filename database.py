"""
OmniSight Database Persistence Layer
====================================
SQLAlchemy ORM models, SQLite session setup, and persistence utilities
for tracking scan execution, viewport metrics, and self-healing verification.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./omnisight.db")

# SQLite needs check_same_thread=False for multithreaded / background task access
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ScanRecord(Base):
    """
    Persistent record of a viewport scan request and its automated findings.
    """
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_id = Column(String(64), unique=True, index=True, nullable=False)
    url = Column(String(512), nullable=False)
    status = Column(String(32), default="pending", index=True, nullable=False)  # pending, processing, completed, failed
    viewports = Column(JSON, default=lambda: ["desktop", "mobile"])
    results = Column(JSON, default=list)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary compatible with both backend API and frontend dashboard."""
        res = self.results or []
        
        # Calculate detected defect issues from metrics
        issue_count = 0
        if isinstance(res, list):
            for r in res:
                metrics = r.get("metrics", {}) if isinstance(r, dict) else {}
                if metrics.get("has_horizontal_overflow"):
                    issue_count += 1
                for b in metrics.get("buttons", []):
                    if b.get("is_off_screen"):
                        issue_count += 1

        return {
            "id": self.scan_id,
            "scan_id": self.scan_id,
            "url": self.url,
            "target": self.url,
            "status": self.status,
            "state": self.status,
            "viewports": self.viewports or ["desktop", "mobile"],
            "results": res,
            "issue_count": issue_count,
            "issues_found": issue_count,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def init_db():
    """Create all tables in the database if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency to provide a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
