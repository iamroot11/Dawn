import pytest
from app.services import hierarchy as hc
from app.services import sources as sc
from app.models import Source, SourceExercise, Track, RatedDifficulty, DifficultyScheme

# ===================================================================
# 1. SOURCE TESTS
# ===================================================================

def test_create_and_read_source(db):
    """Test creating a source linked to a valid topic."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    rotational = hc.create_topic(
        db=db, 
        topic_name="Rotational Dynamics", 
        subject_id=physics.subject_id, 
        track=Track.JEE
    )

    source = sc.create_source(
        db=db,
        book_name="HC Verma Vol 1",
        topic_id=rotational.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.MEDIUM,
        difficulty_scheme=DifficultyScheme.LABELED,
        total_problems=50,
        problems_solved=10
    )

    assert source.source_id is not None
    assert source.book_name == "HC Verma Vol 1"
    assert source.topic_id == rotational.topic_id
    assert source.problems_solved == 10
    assert source.is_active is True


def test_update_source(db):
    """Test updating source fields."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    rotational = hc.create_topic(db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track=Track.JEE)

    source = sc.create_source(
        db=db,
        book_name="Irodov",
        topic_id=rotational.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.HARD,
        difficulty_scheme=DifficultyScheme.UNKNOWN,
        total_problems=30,
        problems_solved=0
    )

    updated_source = sc.update_source(
        db=db,
        source_id=source.source_id,
        new_name="IE Irodov - Basic Laws of Mechanics",
        new_topic_id=rotational.topic_id,
        new_track=None,
        new_rated_difficulty=None,
        new_difficulty_scheme=None,
        new_total_problems=35,
        new_problems_solved=5
    )

    assert updated_source.book_name == "IE Irodov - Basic Laws of Mechanics"
    assert updated_source.total_problems == 35
    assert updated_source.problems_solved == 5


def test_soft_delete_source(db):
    """Test soft deleting a source."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    rotational = hc.create_topic(db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track=Track.JEE)

    source = sc.create_source(
        db=db,
        book_name="Cengage",
        topic_id=rotational.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.HARD,
        difficulty_scheme=DifficultyScheme.LABELED,
        total_problems=100,
        problems_solved=20
    )

    deleted_source = sc.soft_delete_source(db=db, source_id=source.source_id)
    assert deleted_source.is_active is False

    # Ensure record remains in DB
    db_source = db.query(Source).filter_by(source_id=source.source_id).first()
    assert db_source is not None
    assert db_source.is_active is False


def test_source_not_found_raises_error(db):
    """Test updating or deleting a non-existent source raises ValueError."""
    with pytest.raises(ValueError, match="Source 999 not found"):
        sc.update_source(
            db=db,
            source_id=999,
            new_name="Ghost Book",
            new_topic_id=None,
            new_track=None,
            new_rated_difficulty=None,
            new_difficulty_scheme=None,
            new_total_problems=None,
            new_problems_solved=None
        )

    with pytest.raises(ValueError, match="Source 999 not found"):
        sc.soft_delete_source(db=db, source_id=999)


# ===================================================================
# 2. SOURCE EXERCISE TESTS
# ===================================================================

def test_create_and_update_source_exercise(db):
    """Test creating and updating a source exercise."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    rotational = hc.create_topic(db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track=Track.JEE)

    source = sc.create_source(
        db=db,
        book_name="HC Verma Vol 1",
        topic_id=rotational.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.MEDIUM,
        difficulty_scheme=DifficultyScheme.LABELED,
        total_problems=50,
        problems_solved=10
    )

    # Create Exercise
    ex = sc.create_source_exercise(
        db=db,
        source_id=source.source_id,
        exercise_number="Ex 1A",
        problems_in_exercise=15,
        problems_solved=5
    )

    assert ex.exercise_id is not None
    assert ex.source_id == source.source_id
    assert ex.exercise_number == "Ex 1A"

    # Update Exercise
    updated_ex = sc.update_source_exercise(
        db=db,
        exercise_id=ex.exercise_id,
        new_source_id=None,
        new_exercise_number="Exercise 1-A",
        new_problems_in_exercise=20,
        new_problems_solved=10
    )

    assert updated_ex.exercise_number == "Exercise 1-A"
    assert updated_ex.problems_in_exercise == 20
    assert updated_ex.problems_solved == 10


def test_soft_delete_exercise(db):
    """Test soft deleting a source exercise."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    rotational = hc.create_topic(db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track=Track.JEE)

    source = sc.create_source(
        db=db,
        book_name="HC Verma Vol 1",
        topic_id=rotational.topic_id,
        track=Track.JEE,
        rated_difficulty=RatedDifficulty.MEDIUM,
        difficulty_scheme=DifficultyScheme.LABELED,
        total_problems=50,
        problems_solved=10
    )

    ex = sc.create_source_exercise(
        db=db,
        source_id=source.source_id,
        exercise_number="Ex 1B",
        problems_in_exercise=10,
        problems_solved=2
    )

    deleted_ex = sc.soft_delete_exercise(db=db, exercise_id=ex.exercise_id)
    assert deleted_ex.is_active is False

    db_ex = db.query(SourceExercise).filter_by(exercise_id=ex.exercise_id).first()
    assert db_ex is not None
    assert db_ex.is_active is False


def test_exercise_not_found_raises_error(db):
    """Test updating or deleting a non-existent exercise raises ValueError."""
    with pytest.raises(ValueError, match="Source Exercise 999 not found"):
        sc.update_source_exercise(
            db=db,
            exercise_id=999,
            new_source_id=None,
            new_exercise_number="Ghost Ex",
            new_problems_in_exercise=None,
            new_problems_solved=None
        )

    with pytest.raises(ValueError, match="Source Exercise 999 not found"):
        sc.soft_delete_exercise(db=db, exercise_id=999)