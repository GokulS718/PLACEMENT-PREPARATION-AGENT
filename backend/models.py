import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Fetch connection string, fallback to SQLite locally
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./placement_prep.db")

# Setup SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """
    User Table containing student profile information.
    """
    __tablename__ = "users"

    email = Column(String(100), primary_key=True, index=True)
    password = Column(String(100), nullable=True) # Password field added
    name = Column(String(100), nullable=True)
    branch = Column(String(100), nullable=True)
    year = Column(String(50), nullable=True)
    cgpa = Column(String(20), nullable=True)
    skills = Column(Text, nullable=True)
    goals = Column(Text, nullable=True) # Target company/position
    resume_text = Column(Text, nullable=True)
    prep_level = Column(String(50), default="intermediate")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    performance_records = relationship("PerformanceLog", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("ResourceRecommendation", back_populates="user", cascade="all, delete-orphan")

class SessionState(Base):
    """
    SessionState Table storing serialized state metadata of the active LangGraph workflow.
    """
    __tablename__ = "session_states"

    user_id = Column(String(100), primary_key=True, index=True)
    state_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PerformanceLog(Base):
    """
    PerformanceLog Table saving history of question prompts, user responses, scores, and feedback.
    """
    __tablename__ = "performance_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), ForeignKey("users.email"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    question_id = Column(String(100), nullable=True)
    topic = Column(String(100), nullable=True)
    difficulty = Column(String(50), nullable=True)
    question_text = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)

    user = relationship("User", back_populates="performance_records")

class ResourceRecommendation(Base):
    """
    ResourceRecommendation Table storing curated roadmaps.
    """
    __tablename__ = "resource_recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), ForeignKey("users.email"), index=True)
    topic = Column(String(100), nullable=False)
    resources = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recommendations")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
