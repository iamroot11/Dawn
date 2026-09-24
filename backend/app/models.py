"""
DAWN — SQLAlchemy models.

Mirrors docs/SCHEMA.md exactly. If you change something here, update
SCHEMA.md to match — that file is the reference, this is the implementation.
"""

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Every table below inherits from this. Nothing to configure here yet —
    it's just the shared foundation SQLAlchemy uses to track your models."""
    pass


# ============================================================
# Enums — every fixed-choice field from SCHEMA.md gets one.
# This is what stops "Corect" or "medum" typos from silently
# corrupting the dataset.
# ============================================================

class Track(str, enum.Enum):
    JEE = "JEE"
    BOARD = "Board"
    BOTH = "Both"


class RatedDifficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    UNRATED = "Unrated"


class DifficultyScheme(str, enum.Enum):
    LABELED = "labeled"
    EXERCISE_ORDINAL = "exercise-ordinal"
    UNKNOWN = "unknown"


class CalibrationConfidence(str, enum.Enum):
    UNCALIBRATED = "uncalibrated"
    PROVISIONAL = "provisional"
    CALIBRATED = "calibrated"


class SubjectiveDifficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class Correctness(str, enum.Enum):
    CORRECT = "Correct"
    INCORRECT = "Incorrect"
    PARTIAL = "Partial"
    PENDING = "Pending"


class ErrorType(str, enum.Enum):
    NIL = "Nil"
    CONCEPTUAL = "Conceptual"
    SILLY = "Silly"
    CALCULATION = "Calculation"
    STRATEGIC = "Strategic"
    TIME_PRESSURE = "Time-pressure"
    MISREAD = "Misread"


class ConfidenceRating(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class QueueStatus(str, enum.Enum):
    PENDING = "pending"
    DIAGNOSED = "diagnosed"
    RESOLVED = "resolved"


class TestType(str, enum.Enum):
    TWT = "TWT"
    MT = "MT"


class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class SyllabusStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# ============================================================
# Subjects / Topics / Subtopics — full three-level hierarchy,
# referenced everywhere by foreign key rather than free text
# (Decisions log entry).
# ============================================================

class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[int] = mapped_column(primary_key=True)
    subject_name: Mapped[str] = mapped_column(String(60))  # "Physics", "Chemistry", "Maths"

    topics: Mapped[list["Topic"]] = relationship(back_populates="subject")


class Topic(Base):
    __tablename__ = "topics"

    topic_id: Mapped[int] = mapped_column(primary_key=True)
    topic_name: Mapped[str] = mapped_column(String(120))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.subject_id"))
    track: Mapped[Track] = mapped_column(default=Track.JEE)

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(back_populates="topic")

 
class Subtopic(Base):
    __tablename__ = "subtopics"

    subtopic_id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"))
    subtopic_name: Mapped[str] = mapped_column(String(120))

    topic: Mapped["Topic"] = relationship(back_populates="subtopics")


# ============================================================
# Sources / Source_Exercises
# ============================================================

class Source(Base):
    __tablename__ = "sources"

    source_id: Mapped[int] = mapped_column(primary_key=True)
    book_name: Mapped[str] = mapped_column(String(120))
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"))
    track: Mapped[Track] = mapped_column(default=Track.JEE)
    rated_difficulty: Mapped[RatedDifficulty] = mapped_column(default=RatedDifficulty.UNRATED)
    difficulty_scheme: Mapped[DifficultyScheme] = mapped_column(default=DifficultyScheme.UNKNOWN)
    total_problems: Mapped[int] = mapped_column(default=0)
    problems_solved: Mapped[int] = mapped_column(default=0)
    calibrated_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_confidence: Mapped[CalibrationConfidence] = mapped_column(
        default=CalibrationConfidence.UNCALIBRATED
    )

    topic: Mapped["Topic"] = relationship()
    exercises: Mapped[list["SourceExercise"]] = relationship(back_populates="source")


class SourceExercise(Base):
    __tablename__ = "source_exercises"

    exercise_id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    exercise_number: Mapped[str] = mapped_column(String(30))  # e.g. "Exercise 3"
    problems_in_exercise: Mapped[int] = mapped_column(default=0)
    problems_solved: Mapped[int] = mapped_column(default=0)
    calibrated_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="exercises")


# ============================================================
# Sessions
# (fixed metadata set once at session start — see Decisions log)
# ============================================================

class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"))
    subtopic_id: Mapped[int] = mapped_column(ForeignKey("subtopics.subtopic_id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    track: Mapped[Track] = mapped_column(default=Track.JEE)
    starting_question_number: Mapped[int] = mapped_column(default=1)
    batch_size: Mapped[int] = mapped_column(default=10)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    topic: Mapped["Topic"] = relationship()
    subtopic: Mapped["Subtopic"] = relationship()
    source: Mapped["Source"] = relationship()
    questions: Mapped[list["Question"]] = relationship(back_populates="session")


# ============================================================
# Questions
# (every attempt — raw, append-only; a redo is a NEW row,
# linked back via original_question_id, never an overwrite)
# ============================================================

class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.session_id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_exercises.exercise_id"), nullable=True
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"))
    subtopic_id: Mapped[int] = mapped_column(ForeignKey("subtopics.subtopic_id"))
    track: Mapped[Track] = mapped_column(default=Track.JEE)

    question_number: Mapped[int] = mapped_column(Integer)
    subjective_difficulty: Mapped[SubjectiveDifficulty | None] = mapped_column(nullable=True)
    correctness: Mapped[Correctness] = mapped_column(default=Correctness.PENDING)
    error_type: Mapped[ErrorType] = mapped_column(default=ErrorType.NIL)

    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    position_in_session: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_rating: Mapped[ConfidenceRating | None] = mapped_column(nullable=True)

    original_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.question_id"), nullable=True
    )
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    session: Mapped["Session"] = relationship(back_populates="questions")
    source: Mapped["Source"] = relationship()
    exercise: Mapped["SourceExercise | None"] = relationship()
    topic: Mapped["Topic"] = relationship()
    subtopic: Mapped["Subtopic"] = relationship()
    # self-referential relationship: the original attempt this row is a redo of
    original_question: Mapped["Question | None"] = relationship(remote_side=[question_id])


# ============================================================
# ErrorQueue
# ============================================================

class ErrorQueueItem(Base):
    __tablename__ = "error_queue"

    queue_id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.question_id"))
    error_type: Mapped[ErrorType] = mapped_column()
    times_reviewed: Mapped[int] = mapped_column(default=0)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[QueueStatus] = mapped_column(default=QueueStatus.PENDING)

    question: Mapped["Question"] = relationship()


# ============================================================
# Tests (TWT / MT)
# ============================================================

class Test(Base):
    __tablename__ = "tests"

    test_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[TestType] = mapped_column()
    track: Mapped[Track] = mapped_column(default=Track.JEE)
    subject_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    paper_pdf_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    answer_key_pdf_path: Mapped[str | None] = mapped_column(String(255), nullable=True)


# ============================================================
# Assignments (teacher homework)
# ============================================================

class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.source_id"), nullable=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.topic_id"))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AssignmentStatus] = mapped_column(default=AssignmentStatus.ASSIGNED)

    source: Mapped["Source | None"] = relationship()
    topic: Mapped["Topic"] = relationship()


# ============================================================
# Board_Syllabus
# ============================================================

class BoardSyllabus(Base):
    __tablename__ = "board_syllabus"

    syllabus_id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(60))
    chapter: Mapped[str] = mapped_column(String(120))
    # nullable on purpose — only link when this chapter genuinely overlaps
    # JEE content; leave null when Board's framing/depth differs too much
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.topic_id"), nullable=True)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[SyllabusStatus] = mapped_column(default=SyllabusStatus.NOT_STARTED)

    topic: Mapped["Topic | None"] = relationship()