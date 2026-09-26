# Handles creating Sources and Source Exercises
from typing import Optional, List
from sqlalchemy.orm import Session as DBSession
from app.models import Source, SourceExercise, Track, RatedDifficulty, DifficultyScheme

# ==========================================
# Sources
# ==========================================

def create_source(
    db: DBSession,
    book_name: str,
    topic_id: int,
    track: Track,
    rated_difficulty: RatedDifficulty,
    difficulty_scheme: DifficultyScheme,
    total_problems: int,
    problems_solved: int
) -> Source:
    source = Source(
        book_name = book_name,
        topic_id = topic_id,
        track = track,
        rated_difficulty = rated_difficulty,
        difficulty_scheme = difficulty_scheme,
        total_problems = total_problems,
        problems_solved = problems_solved
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    return source

def update_source(
    db: DBSession,
    source_id: int,
    new_name: Optional[str],
    new_topic_id: Optional[int],
    new_track: Optional[Track],
    new_rated_difficulty: Optional[RatedDifficulty],
    new_difficulty_scheme: Optional[DifficultyScheme],
    new_total_problems: Optional[int],
    new_problems_solved: Optional[int]
) -> Source:
    source = db.query(Source).filter(
        Source.source_id == source_id
    ).first()
    
    if not source:
        raise ValueError(f"Source {source_id} not found")
    if new_name is not None:
        source.book_name = new_name
    if new_topic_id is not None:
        source.topic_id = new_topic_id
    if new_track is not None:
        source.track = new_track
    if new_rated_difficulty is not None:
        source.rated_difficulty = new_rated_difficulty
    if new_difficulty_scheme is not None:
        source.difficulty_scheme = new_difficulty_scheme
    if new_total_problems is not None:
        source.total_problems = new_total_problems
    if new_problems_solved is not None:
        source.problems_solved = new_problems_solved
    
    db.commit()
    db.refresh(source)
    
    return source

def soft_delete_source(db: DBSession, source_id: int) -> Source:
    source = db.query(Source).filter(Source.source_id == source_id).first()
    
    if not source:
        raise ValueError(f"Source {source_id} not found")
    
    source.is_active = False

    db.commit()
    db.refresh(source)
    
    return source

# ==========================================
# Source Exercises
# ==========================================

def create_source_exercise(
    db: DBSession,
    source_id: int,
    exercise_number: str,
    problems_in_exercise: int,
    problems_solved: int
) -> SourceExercise:
    exercise = SourceExercise(
        source_id = source_id,
        exercise_number = exercise_number,
        problems_in_exercise = problems_in_exercise,
        problems_solved = problems_solved
    )
    
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise

def update_source_exercise(
    db: DBSession,
    exercise_id: int,
    new_source_id: Optional[int],
    new_exercise_number: Optional[str],
    new_problems_in_exercise: Optional[int],
    new_problems_solved: Optional[int]
) -> SourceExercise:
    exercise = db.query(SourceExercise).filter(
        SourceExercise.exercise_id == exercise_id
    ).first()
    
    if not exercise:
        raise ValueError(f"Source Exercise {exercise_id} not found")

    if new_source_id is not None:
        exercise.source_id = new_source_id
    if new_exercise_number is not None:
        exercise.exercise_number = new_exercise_number
    if new_problems_in_exercise is not None:
        exercise.problems_in_exercise = new_problems_in_exercise
    if new_problems_solved is not None:
        exercise.problems_solved = new_problems_solved
    
    db.commit()
    db.refresh(exercise)
    
    return exercise

def soft_delete_exercise(db: DBSession, exercise_id: int) -> SourceExercise:
    exercise = db.query(SourceExercise).filter(
        SourceExercise.exercise_id == exercise_id
    ).first()
    
    if not exercise:
        raise ValueError(f"Source Exercise {exercise_id} not found")
    
    exercise.is_active = False
    db.commit()
    db.refresh(exercise)
    
    return exercise