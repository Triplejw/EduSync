from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# SQLite Database (Simple, Single File)
DATABASE_URL = "sqlite:///./edusync.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- TABLES ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # "teacher" or "student"
    full_name = Column(String)


class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    subject_name = Column(String, nullable=True)  # e.g., "Mathematics", "Physics"
    teacher_id = Column(Integer, ForeignKey("users.id"))


class ClassroomEnrollment(Base):
    __tablename__ = "classroom_enrollments"
    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # Composite index for common query pattern: find all students in a classroom
    __table_args__ = (
        Index("ix_enrollment_classroom_user", "classroom_id", "user_id"),
    )


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    file_path = Column(String, nullable=True)  # Path to uploaded file
    raw_text = Column(Text, default="")  # Original extracted text (content_text in spec)
    summary = Column(Text, default="")
    flashcards_json = Column(Text, default="[]")
    quiz_json = Column(Text, default="[]")
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    quiz_json = Column(Text)  # The quiz questions
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    score = Column(Float)  # Percentage 0-100
    answers_json = Column(Text)  # Store submitted answers
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for finding a user's submission for an assignment
    __table_args__ = (
        Index("ix_submission_user_assignment", "user_id", "assignment_id"),
    )


class LearningSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), index=True)
    scroll_signal = Column(Text)
    engagement_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Composite index for finding sessions by user and material
    __table_args__ = (
        Index("ix_session_user_material", "user_id", "material_id"),
    )

# Create/Update Tables
Base.metadata.create_all(bind=engine)