# Handles Sessions and per-question logging (start/pause/resume/complete/grade/end).
#
# Scope: logging only. No accuracy, calibration, decay, or ErrorQueue-scheduling
# math lives here — that's for separate modules once this layer is solid.
#
# Core mechanic: a Question row is created up front (started_at set, everything
# else blank) the moment it becomes "current." It's filled in when completed.
# The "currently open" question for a session is just the row with
# timestamp IS NULL — there's no separate pointer field on Session for it.

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session as DBSession
from app.models import (
    Session,
    Question,
    Source,
    SourceExercise,
    Track,
    SubjectiveDifficulty,
    Correctness,
    ErrorType,
    ConfidenceRating,
)


# ==========================================
# SESSION LIFECYCLE
# ==========================================

def start_session(
    db: DBSession,
    topic_id: int,
    source_id: int,
    track: Track,
    starting_question_number: int = 1,
    subtopic_id: Optional[int] = None,
    exercise_id: Optional[int] = None,
    batch_size: int = 10
) -> Session:
    """Creates the Session row and immediately opens its first question row."""
    session = Session(
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        source_id=source_id,
        exercise_id=exercise_id,
        track=track,
        starting_question_number=starting_question_number,
        batch_size=batch_size
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    first_question = Question(
        session_id=session.session_id,
        source_id=source_id,
        exercise_id=exercise_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        track=track,
        question_number=starting_question_number,
        position_in_session=1,
        started_at=datetime.utcnow()
    )
    db.add(first_question)
    db.commit()
    db.refresh(session)

    return session


def pause_session(db: DBSession, session_id: int) -> Session:
    session = _get_session(db, session_id)
    if session.end_time is not None:
        raise ValueError(f"Session {session_id} has already ended.")
    if session.is_paused:
        raise ValueError(f"Session {session_id} is already paused.")

    session.is_paused = True
    session.paused_at = datetime.utcnow()

    db.commit()
    db.refresh(session)
    return session


def resume_session(db: DBSession, session_id: int) -> Session:
    """Shifts the open question's started_at forward by the pause duration,
    so the pause never counts as time spent on that question."""
    session = _get_session(db, session_id)
    if not session.is_paused:
        raise ValueError(f"Session {session_id} is not paused.")

    now = datetime.utcnow()
    pause_duration = now - session.paused_at

    open_question = _get_open_question(db, session_id)
    if open_question is not None:
        open_question.started_at = open_question.started_at + pause_duration

    session.total_paused_seconds += int(pause_duration.total_seconds())
    session.is_paused = False
    session.paused_at = None

    db.commit()
    db.refresh(session)
    return session


def end_session(
    db: DBSession,
    session_id: int,
    subjective_difficulty: Optional[SubjectiveDifficulty] = None,
    confidence_rating: Optional[ConfidenceRating] = None,
    photo_path: Optional[str] = None
) -> Dict:
    """
    Finishes the currently-open question (if there is one) exactly like a normal
    completion, then ends the session WITHOUT opening a new question row.

    Does not force grading. Returns the session plus any completed-but-ungraded
    questions in it, so the caller can prompt for a grading pass.
    """
    session = _get_session(db, session_id)
    if session.end_time is not None:
        raise ValueError(f"Session {session_id} has already ended.")
    if session.is_paused:
        raise ValueError(f"Session {session_id} is paused — resume it before ending.")

    open_question = _get_open_question(db, session_id)
    if open_question is not None:
        if subjective_difficulty is None:
            raise ValueError(
                "subjective_difficulty is required to close out the open question."
            )
        _fill_in_completion(
            db, open_question, subjective_difficulty, confidence_rating, photo_path
        )

    session.end_time = datetime.utcnow()
    db.commit()
    db.refresh(session)

    ungraded_questions = db.query(Question).filter(
        Question.session_id == session_id,
        Question.timestamp.isnot(None),
        Question.correctness == Correctness.PENDING
    ).all()

    return {"session": session, "ungraded_questions": ungraded_questions}


# ==========================================
# QUESTION LOGGING
# ==========================================

def complete_question(
    db: DBSession,
    session_id: int,
    subjective_difficulty: SubjectiveDifficulty,
    confidence_rating: Optional[ConfidenceRating] = None,
    photo_path: Optional[str] = None
) -> Tuple[Question, bool]:
    """
    Fills in the currently-open question row (timing + difficulty; correctness
    stays Pending until grading). If this doesn't complete a batch, opens the
    next question row right away. If it does, no new row is opened — grade_batch
    is responsible for continuing the session afterward.

    Returns (completed_question, batch_complete).
    """
    session = _get_session(db, session_id)
    if session.end_time is not None:
        raise ValueError(f"Session {session_id} has already ended.")
    if session.is_paused:
        raise ValueError(f"Session {session_id} is paused — resume it before logging a question.")

    open_question = _get_open_question(db, session_id)
    if open_question is None:
        raise ValueError(f"No open question found for session {session_id}.")

    _fill_in_completion(
        db, open_question, subjective_difficulty, confidence_rating, photo_path
    )

    source = db.query(Source).filter(Source.source_id == open_question.source_id).first()
    exercise = None
    if open_question.exercise_id is not None:
        exercise = db.query(SourceExercise).filter(
            SourceExercise.exercise_id == open_question.exercise_id
        ).first()

    batch_complete = _is_batch_complete(db, session, source, exercise)

    if not batch_complete:
        _open_next_question(db, session, open_question)

    return open_question, batch_complete


def grade_batch(
    db: DBSession,
    session_id: int,
    results: List[Dict]
) -> List[Question]:
    """
    results: list of {"question_id": int, "correctness": Correctness, "error_type": ErrorType}

    Writes correctness/error_type onto each row. Does NOT touch pause state —
    session duration is meant to include grading time, not just problem-solving
    time, so grading never pauses the session.

    If nothing is currently open (a batch boundary was just hit) and the
    exercise/source still has problems left and the session hasn't ended,
    opens the next question row so the session can continue.
    """
    session = _get_session(db, session_id)

    graded: List[Question] = []
    for result in results:
        question = db.query(Question).filter(
            Question.question_id == result["question_id"],
            Question.session_id == session_id
        ).first()
        if question is None:
            raise ValueError(
                f"Question {result['question_id']} not found in session {session_id}."
            )
        question.correctness = result["correctness"]
        question.error_type = result["error_type"]
        graded.append(question)

    db.commit()
    for question in graded:
        db.refresh(question)

    if session.end_time is None and _get_open_question(db, session_id) is None:
        source = db.query(Source).filter(Source.source_id == session.source_id).first()
        exercise = None
        if session.exercise_id is not None:
            exercise = db.query(SourceExercise).filter(
                SourceExercise.exercise_id == session.exercise_id
            ).first()

        if not _is_exhausted(source, exercise):
            reference_question = _get_last_question(db, session_id)
            if reference_question is not None:
                _open_next_question(db, session, reference_question)

    return graded


# ==========================================
# Internal helpers
# ==========================================

def _get_session(db: DBSession, session_id: int) -> Session:
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found.")
    return session


def _get_open_question(db: DBSession, session_id: int) -> Optional[Question]:
    return db.query(Question).filter(
        Question.session_id == session_id,
        Question.timestamp.is_(None)
    ).first()


def _get_last_question(db: DBSession, session_id: int) -> Optional[Question]:
    return db.query(Question).filter(
        Question.session_id == session_id
    ).order_by(Question.position_in_session.desc()).first()


def _fill_in_completion(
    db: DBSession,
    question: Question,
    subjective_difficulty: SubjectiveDifficulty,
    confidence_rating: Optional[ConfidenceRating],
    photo_path: Optional[str]
) -> None:
    """Fills timing + difficulty on an open question row and bumps the raw
    problems_solved counters used for batch-boundary detection. Correctness
    and error_type are left untouched — those are set at grade_batch."""
    now = datetime.utcnow()
    question.timestamp = now
    question.time_taken_seconds = int((now - question.started_at).total_seconds())
    question.subjective_difficulty = subjective_difficulty
    question.confidence_rating = confidence_rating
    question.photo_path = photo_path

    source = db.query(Source).filter(Source.source_id == question.source_id).first()
    if source is not None:
        source.problems_solved += 1

    if question.exercise_id is not None:
        exercise = db.query(SourceExercise).filter(
            SourceExercise.exercise_id == question.exercise_id
        ).first()
        if exercise is not None:
            exercise.problems_solved += 1

    db.commit()
    db.refresh(question)


def _is_exhausted(source: Optional[Source], exercise: Optional[SourceExercise]) -> bool:
    """An exercise, if set, governs exhaustion; otherwise the source does."""
    if exercise is not None:
        return exercise.problems_solved >= exercise.problems_in_exercise
    if source is not None:
        return source.problems_solved >= source.total_problems
    return False


def _is_batch_complete(
    db: DBSession,
    session: Session,
    source: Optional[Source],
    exercise: Optional[SourceExercise]
) -> bool:
    """A batch ends when batch_size questions have been completed-but-ungraded,
    OR the exercise/source has run out of problems — whichever comes first."""
    pending_completed = db.query(Question).filter(
        Question.session_id == session.session_id,
        Question.timestamp.isnot(None),
        Question.correctness == Correctness.PENDING
    ).count()

    if pending_completed >= session.batch_size:
        return True

    return _is_exhausted(source, exercise)


def _open_next_question(
    db: DBSession,
    session: Session,
    reference_question: Question
) -> Question:
    next_question = Question(
        session_id=session.session_id,
        source_id=session.source_id,
        exercise_id=session.exercise_id,
        topic_id=session.topic_id,
        subtopic_id=session.subtopic_id,
        track=session.track,
        question_number=reference_question.question_number + 1,
        position_in_session=reference_question.position_in_session + 1,
        started_at=datetime.utcnow()
    )
    db.add(next_question)
    db.commit()
    db.refresh(next_question)
    return next_question