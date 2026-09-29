from datetime import datetime, timedelta

import pytest
from app.services import sessions as ss
from app.services import hierarchy as hc
from app.services import sources as sc
from app.models import (
    Question,
    Track,
    RatedDifficulty,
    DifficultyScheme,
    SubjectiveDifficulty,
    Correctness,
    ErrorType,
    ConfidenceRating,
)


# ==============================================
# Helpers — every test needs a topic + source to
# hang a session off of, so set that up once here.
# ==============================================

def _make_topic_and_source(db, total_problems: int = 50):
    physics = hc.create_subject(db=db, subject_name="Physics")
    topic = hc.create_topic(
        db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track=Track.JEE
    )
    source = sc.create_source(
        db=db,
        book_name="HC Verma Part 1",
        topic_id=topic.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.MEDIUM,
        difficulty_scheme=DifficultyScheme.LABELED,
        total_problems=total_problems,
        problems_solved=0
    )
    return topic, source


def _open_question(db, session_id):
    """Grabs the currently-open (timestamp IS NULL) question for a session."""
    return db.query(Question).filter(
        Question.session_id == session_id,
        Question.timestamp.is_(None)
    ).first()


# ==============================================
# 1. Starting a session
# ==============================================

def test_start_session_creates_session_and_first_question(db):
    topic, source = _make_topic_and_source(db)

    study_session = ss.start_session(
        db=db,
        topic_id=topic.topic_id,
        source_id=source.source_id,
        track=Track.JEE,
        batch_size=5
    )

    assert study_session.session_id is not None
    assert study_session.is_paused is False
    assert study_session.end_time is None
    assert study_session.start_time is not None

    open_question = _open_question(db, study_session.session_id)
    assert open_question is not None
    assert open_question.position_in_session == 1
    assert open_question.question_number == study_session.starting_question_number
    assert open_question.started_at is not None
    assert open_question.timestamp is None
    assert open_question.correctness == Correctness.PENDING


# ==============================================
# 2. Completing questions & batch boundaries
# ==============================================

def test_complete_question_opens_next_when_batch_not_full(db):
    topic, source = _make_topic_and_source(db, total_problems=100)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE, batch_size=3
    )

    completed, batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.MEDIUM
    )

    assert batch_complete is False
    assert completed.timestamp is not None
    assert completed.time_taken_seconds is not None
    assert completed.time_taken_seconds >= 0
    assert completed.correctness == Correctness.PENDING  # ungraded until grade_batch

    db.refresh(source)
    assert source.problems_solved == 1

    next_open = _open_question(db, study_session.session_id)
    assert next_open is not None
    assert next_open.position_in_session == 2


def test_batch_completes_at_batch_size(db):
    topic, source = _make_topic_and_source(db, total_problems=100)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE, batch_size=2
    )

    _, first_batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
    )
    assert first_batch_complete is False

    _, second_batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.HARD
    )
    assert second_batch_complete is True

    # No new question row should have been opened once the batch closed
    assert _open_question(db, study_session.session_id) is None

    logged = db.query(Question).filter(Question.session_id == study_session.session_id).all()
    assert len(logged) == 2
    assert all(q.correctness == Correctness.PENDING for q in logged)


def test_batch_completes_when_exercise_runs_out_before_batch_size(db):
    topic, source = _make_topic_and_source(db, total_problems=100)
    exercise = sc.create_source_exercise(
        db=db,
        source_id=source.source_id,
        exercise_number="Exercise 1",
        problems_in_exercise=1,
        problems_solved=0
    )
    study_session = ss.start_session(
        db=db,
        topic_id=topic.topic_id,
        source_id=source.source_id,
        track=Track.JEE,
        exercise_id=exercise.exercise_id,
        batch_size=10  # deliberately larger than the exercise can supply
    )

    _, batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.MEDIUM
    )

    assert batch_complete is True  # exhaustion closed the batch, not batch_size
    assert _open_question(db, study_session.session_id) is None

    db.refresh(exercise)
    assert exercise.problems_solved == 1


# ==============================================
# 3. Pause / resume
# ==============================================

def test_pause_then_resume_shifts_open_question_started_at(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )

    original_started_at = _open_question(db, study_session.session_id).started_at

    ss.pause_session(db=db, session_id=study_session.session_id)

    # Backdate paused_at to simulate a real ~100 second pause without sleeping in the test.
    db.refresh(study_session)
    study_session.paused_at = datetime.utcnow() - timedelta(seconds=100)
    db.commit()

    resumed = ss.resume_session(db=db, session_id=study_session.session_id)

    assert resumed.is_paused is False
    assert resumed.paused_at is None
    assert resumed.total_paused_seconds >= 99  # allow a little slack for test execution time

    shifted_question = _open_question(db, study_session.session_id)
    shift = (shifted_question.started_at - original_started_at).total_seconds()
    assert shift >= 99


def test_pause_twice_raises(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )
    ss.pause_session(db=db, session_id=study_session.session_id)

    with pytest.raises(ValueError, match="already paused"):
        ss.pause_session(db=db, session_id=study_session.session_id)


def test_resume_without_pause_raises(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )

    with pytest.raises(ValueError, match="is not paused"):
        ss.resume_session(db=db, session_id=study_session.session_id)


def test_complete_question_blocked_while_paused(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )
    ss.pause_session(db=db, session_id=study_session.session_id)

    with pytest.raises(ValueError, match="paused"):
        ss.complete_question(
            db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
        )


# ==============================================
# 4. Grading a batch
# ==============================================

def test_grade_batch_writes_results_and_continues_session(db):
    topic, source = _make_topic_and_source(db, total_problems=100)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE, batch_size=2
    )

    q1, _ = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
    )
    q2, batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.HARD
    )
    assert batch_complete is True

    graded = ss.grade_batch(
        db=db,
        session_id=study_session.session_id,
        results=[
            {"question_id": q1.question_id, "correctness": Correctness.CORRECT, "error_type": ErrorType.NIL},
            {"question_id": q2.question_id, "correctness": Correctness.INCORRECT, "error_type": ErrorType.CONCEPTUAL},
        ]
    )

    assert {g.correctness for g in graded} == {Correctness.CORRECT, Correctness.INCORRECT}
    assert q2.error_type == ErrorType.CONCEPTUAL

    # Source has plenty of problems left, so grading should have opened question 3
    next_open = _open_question(db, study_session.session_id)
    assert next_open is not None
    assert next_open.position_in_session == 3


def test_grade_batch_does_not_continue_when_source_exhausted(db):
    topic, source = _make_topic_and_source(db, total_problems=1)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE, batch_size=10
    )

    q1, batch_complete = ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.MEDIUM
    )
    assert batch_complete is True  # source exhausted after 1 problem

    ss.grade_batch(
        db=db,
        session_id=study_session.session_id,
        results=[{"question_id": q1.question_id, "correctness": Correctness.CORRECT, "error_type": ErrorType.NIL}]
    )

    assert _open_question(db, study_session.session_id) is None


def test_grade_batch_unknown_question_raises(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )

    with pytest.raises(ValueError, match="not found"):
        ss.grade_batch(
            db=db,
            session_id=study_session.session_id,
            results=[{"question_id": 9999, "correctness": Correctness.CORRECT, "error_type": ErrorType.NIL}]
        )


# ==============================================
# 5. Ending a session
# ==============================================

def test_end_session_completes_open_question_without_starting_new_one(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )
    ss.complete_question(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
    )  # opens question 2

    result = ss.end_session(
        db=db,
        session_id=study_session.session_id,
        subjective_difficulty=SubjectiveDifficulty.MEDIUM,
        confidence_rating=ConfidenceRating.LOW
    )

    ended_session = result["session"]
    assert ended_session.end_time is not None
    assert _open_question(db, study_session.session_id) is None

    all_questions = db.query(Question).filter(Question.session_id == study_session.session_id).all()
    assert len(all_questions) == 2  # nothing new opened by end_session itself

    # Both questions were completed but never graded
    assert len(result["ungraded_questions"]) == 2


def test_end_session_requires_difficulty_when_question_still_open(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )

    with pytest.raises(ValueError, match="subjective_difficulty is required"):
        ss.end_session(db=db, session_id=study_session.session_id)


def test_end_session_twice_raises(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )
    ss.end_session(
        db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
    )

    with pytest.raises(ValueError, match="already ended"):
        ss.end_session(
            db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
        )


def test_end_session_while_paused_raises(db):
    topic, source = _make_topic_and_source(db)
    study_session = ss.start_session(
        db=db, topic_id=topic.topic_id, source_id=source.source_id, track=Track.JEE
    )
    ss.pause_session(db=db, session_id=study_session.session_id)

    with pytest.raises(ValueError, match="paused"):
        ss.end_session(
            db=db, session_id=study_session.session_id, subjective_difficulty=SubjectiveDifficulty.EASY
        )