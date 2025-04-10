"""Database manager for job screening system."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import json
from typing import Dict, Any, List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

Base = declarative_base()

class JobDescription(Base):
    """Job description table."""
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), unique=True)
    job_title = Column(String(100))
    raw_text = Column(Text)
    summary = Column(Text)
    skills = Column(Text)  # JSON string of skills
    responsibilities = Column(Text)  # JSON string of responsibilities
    qualifications = Column(Text)  # JSON string of qualifications
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "job_title": self.job_title,
            "raw_text": self.raw_text,
            "summary": self.summary,
            "skills": json.loads(self.skills) if self.skills else [],
            "responsibilities": json.loads(self.responsibilities) if self.responsibilities else [],
            "qualifications": json.loads(self.qualifications) if self.qualifications else [],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Candidate(Base):
    """Candidate table."""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(50))
    resume_path = Column(String(255))
    parsed_resume = Column(Text)  # JSON string of parsed resume
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "resume_path": self.resume_path,
            "parsed_resume": json.loads(self.parsed_resume) if self.parsed_resume else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Match(Base):
    """Match table for job-candidate matches."""
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"))
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    score = Column(Float)
    shortlisted = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    job = relationship("JobDescription")
    candidate = relationship("Candidate")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "candidate_id": self.candidate_id,
            "score": self.score,
            "shortlisted": self.shortlisted,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection."""
        self.engine = create_engine(db_url or DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get a new session."""
        return self.Session()
    
    # Job Description Methods
    def save_job_description(self, job_id: str, job_title: str, raw_text: str) -> JobDescription:
        """Save a new job description."""
        with self.get_session() as session:
            jd = JobDescription(
                job_id=job_id,
                job_title=job_title,
                raw_text=raw_text
            )
            session.add(jd)
            session.commit()
            session.refresh(jd)
            return jd
    
    def update_job_summary(self, job_id: str, summary: str, skills: List[str], 
                           responsibilities: List[str], qualifications: List[str]) -> JobDescription:
        """Update job description with summary."""
        with self.get_session() as session:
            jd = session.query(JobDescription).filter_by(job_id=job_id).first()
            if jd:
                jd.summary = summary
                jd.skills = json.dumps(skills)
                jd.responsibilities = json.dumps(responsibilities)
                jd.qualifications = json.dumps(qualifications)
                session.commit()
                session.refresh(jd)
            return jd
    
    def get_job_description(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job description by ID."""
        with self.get_session() as session:
            jd = session.query(JobDescription).filter_by(job_id=job_id).first()
            return jd.to_dict() if jd else None
    
    # Candidate Methods
    def save_candidate(self, name: str, email: str, phone: str, resume_path: str) -> Candidate:
        """Save a new candidate."""
        with self.get_session() as session:
            candidate = Candidate(
                name=name,
                email=email,
                phone=phone,
                resume_path=resume_path
            )
            session.add(candidate)
            session.commit()
            session.refresh(candidate)
            return candidate
    
    def update_candidate_resume(self, candidate_id: int, parsed_resume: Dict[str, Any]) -> Candidate:
        """Update candidate with parsed resume."""
        with self.get_session() as session:
            candidate = session.query(Candidate).filter_by(id=candidate_id).first()
            if candidate:
                candidate.parsed_resume = json.dumps(parsed_resume)
                session.commit()
                session.refresh(candidate)
            return candidate
    
    def get_candidate(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Get candidate by ID."""
        with self.get_session() as session:
            candidate = session.query(Candidate).filter_by(id=candidate_id).first()
            return candidate.to_dict() if candidate else None
    
    # Match Methods
    def save_match(self, job_id: int, candidate_id: int, score: float) -> Match:
        """Save a job-candidate match."""
        with self.get_session() as session:
            match = Match(
                job_id=job_id,
                candidate_id=candidate_id,
                score=score,
                shortlisted=score >= 0.8  # Using 0.8 as threshold
            )
            session.add(match)
            session.commit()
            session.refresh(match)
            return match
    
    def update_match_email_sent(self, match_id: int) -> Match:
        """Update match with email sent status."""
        with self.get_session() as session:
            match = session.query(Match).filter_by(id=match_id).first()
            if match:
                match.email_sent = True
                match.email_sent_at = datetime.datetime.utcnow()
                session.commit()
                session.refresh(match)
            return match
    
    def get_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get match by ID."""
        with self.get_session() as session:
            match = session.query(Match).filter_by(id=match_id).first()
            return match.to_dict() if match else None
    
    def get_matches_for_job(self, job_id: int, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get all matches for a job, optionally filtered by threshold."""
        with self.get_session() as session:
            query = session.query(Match).filter_by(job_id=job_id)
            if threshold is not None:
                query = query.filter(Match.score >= threshold)
            matches = query.all()
            return [match.to_dict() for match in matches]
    
    def get_shortlisted_candidates(self, job_id: int) -> List[Dict[str, Any]]:
        """Get shortlisted candidates for a job."""
        with self.get_session() as session:
            matches = session.query(Match).filter_by(job_id=job_id, shortlisted=True).all()
            result = []
            for match in matches:
                candidate = session.query(Candidate).filter_by(id=match.candidate_id).first()
                if candidate:
                    data = candidate.to_dict()
                    data["score"] = match.score
                    data["match_id"] = match.id
                    result.append(data)
            return result