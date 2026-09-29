"""
DAWN — HTTP/JSON layer.

Thin Flask wrapper around app/services/*.py. This file does three things and
nothing else: parse a request into plain Python arguments, call a service
function, serialize the result back to JSON. All actual logic (validation,
business rules) lives in the service modules — if you find yourself writing
an if-statement here that isn't about parsing or serializing, it probably
belongs in a service file instead.
"""

import enum
from datetime import date, datetime

from flask import Flask, g, jsonify, request
from sqlalchemy import inspect as sa_inspect

from app.database import SessionLocal
from app.models import (
    Subject,
    Topic,
    Subtopic,
    Source,
    SourceExercise,
    Session as SessionModel,
    Question,
    Track,
    RatedDifficulty,
    DifficultyScheme,
    SubjectiveDifficulty,
    Correctness,
    ErrorType,
    ConfidenceRating,
)
from app.services import hierarchy as hc
from app.services import sources as sc
from app.services import sessions as ss

app = Flask(__name__)


# ==========================================
# DB session lifecycle — one SQLAlchemy
# session per request, closed on teardown.
# ==========================================

def get_db():
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ==========================================
# Error handling — any ValueError raised
# anywhere in the service layer becomes a
# clean 400 response, in one place.
# ==========================================

@app.errorhandler(ValueError)
def handle_value_error(e):
    return jsonify({"error": str(e)}), 400


# ==========================================
# Serialization helpers
# ==========================================

def serialize(obj):
    """Turns a single model row into a JSON-safe dict: enums become their
    .value, dates/datetimes become ISO strings. Only real columns are
    included — relationships are left out to keep responses flat; fetch
    the related object via its own endpoint if you need it."""
    if obj is None:
        return None

    data = {}
    mapper = sa_inspect(obj).mapper # Allows us to inspect the metadata of the sqlalvhemy object
    for column in mapper.columns:
        value = getattr(obj, column.key) # Get column name
        if isinstance(value, enum.Enum):
            value = value.value
        elif isinstance(value, (datetime, date)):
            value = value.isoformat()
        data[column.key] = value
    return data


def serialize_many(objs):
    return [serialize(obj) for obj in objs]


def parse_enum(enum_cls, value, field_name):
    """Converts an incoming JSON string to an enum member, with a clear
    error message if it doesn't match anything."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        valid = [e.value for e in enum_cls]
        raise ValueError(f"Invalid value '{value}' for {field_name}. Expected one of: {valid}")


def body():
    """Request JSON body as a dict, or {} if none was sent."""
    return request.get_json(silent=True) or {}


def get_open_question(db, session_id):
    return db.query(Question).filter(
        Question.session_id == session_id,
        Question.timestamp.is_(None)
    ).first()


# ==========================================
# SUBJECTS
# ==========================================

@app.route("/subjects", methods=["GET"])
def list_subjects():
    db = get_db()
    subjects = db.query(Subject).filter(Subject.is_active == True).all()  # noqa: E712
    return jsonify(serialize_many(subjects))


@app.route("/subjects", methods=["POST"])
def create_subject():
    db = get_db()
    data = body()
    subject = hc.create_subject(db=db, subject_name=data.get("subject_name"))
    return jsonify(serialize(subject)), 201


@app.route("/subjects/<int:subject_id>", methods=["PATCH"])
def update_subject(subject_id):
    db = get_db()
    data = body()
    subject = hc.update_subject(db=db, subject_id=subject_id, new_name=data.get("new_name"))
    return jsonify(serialize(subject))


@app.route("/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    db = get_db()
    subject = hc.soft_delete_subject(db=db, subject_id=subject_id)
    return jsonify(serialize(subject))


# ==========================================
# TOPICS
# ==========================================

@app.route("/topics", methods=["GET"])
def list_topics():
    db = get_db()
    query = db.query(Topic).filter(Topic.is_active == True)  # noqa: E712
    subject_id = request.args.get("subject_id", type=int)
    if subject_id is not None:
        query = query.filter(Topic.subject_id == subject_id)
    return jsonify(serialize_many(query.all()))


@app.route("/topics", methods=["POST"])
def create_topic():
    db = get_db()
    data = body()
    topic = hc.create_topic(
        db=db,
        topic_name=data.get("topic_name"),
        subject_id=data.get("subject_id"),
        track=parse_enum(Track, data.get("track"), "track")
    )
    return jsonify(serialize(topic)), 201


@app.route("/topics/<int:topic_id>", methods=["PATCH"])
def update_topic(topic_id):
    db = get_db()
    data = body()
    topic = hc.update_topic(
        db=db,
        topic_id=topic_id,
        new_name=data.get("new_name"),
        new_subject_id=data.get("new_subject_id"),
        new_track=parse_enum(Track, data.get("new_track"), "new_track")
    )
    return jsonify(serialize(topic))


@app.route("/topics/<int:topic_id>", methods=["DELETE"])
def delete_topic(topic_id):
    db = get_db()
    topic = hc.soft_delete_topic(db=db, topic_id=topic_id)
    return jsonify(serialize(topic))


@app.route("/topics/merge", methods=["POST"])
def merge_topics():
    db = get_db()
    data = body()
    topic = hc.merge_topic(
        db=db,
        source_topic_id=data.get("source_topic_id"),
        target_topic_id=data.get("target_topic_id")
    )
    return jsonify(serialize(topic))


# ==========================================
# SUBTOPICS
# ==========================================

@app.route("/subtopics", methods=["GET"])
def list_subtopics():
    db = get_db()
    query = db.query(Subtopic).filter(Subtopic.is_active == True)  # noqa: E712
    topic_id = request.args.get("topic_id", type=int)
    if topic_id is not None:
        query = query.filter(Subtopic.topic_id == topic_id)
    return jsonify(serialize_many(query.all()))


@app.route("/subtopics", methods=["POST"])
def create_subtopic():
    db = get_db()
    data = body()
    subtopic = hc.create_subtopic(
        db=db, subtopic_name=data.get("subtopic_name"), topic_id=data.get("topic_id")
    )
    return jsonify(serialize(subtopic)), 201


@app.route("/subtopics/<int:subtopic_id>", methods=["PATCH"])
def update_subtopic(subtopic_id):
    db = get_db()
    data = body()
    subtopic = hc.update_subtopic(
        db=db,
        subtopic_id=subtopic_id,
        new_name=data.get("new_name"),
        new_topic_id=data.get("new_topic_id")
    )
    return jsonify(serialize(subtopic))


@app.route("/subtopics/<int:subtopic_id>", methods=["DELETE"])
def delete_subtopic(subtopic_id):
    db = get_db()
    subtopic = hc.soft_delete_subtopic(db=db, subtopic_id=subtopic_id)
    return jsonify(serialize(subtopic))


# ==========================================
# SOURCES
# ==========================================

@app.route("/sources", methods=["GET"])
def list_sources():
    db = get_db()
    query = db.query(Source).filter(Source.is_active == True)  # noqa: E712
    topic_id = request.args.get("topic_id", type=int)
    if topic_id is not None:
        query = query.filter(Source.topic_id == topic_id)
    return jsonify(serialize_many(query.all()))


@app.route("/sources", methods=["POST"])
def create_source():
    db = get_db()
    data = body()
    source = sc.create_source(
        db=db,
        book_name=data.get("book_name"),
        topic_id=data.get("topic_id"),
        track=parse_enum(Track, data.get("track"), "track"),
        rated_difficulty=parse_enum(
            RatedDifficulty, data.get("rated_difficulty", "Unrated"), "rated_difficulty"
        ),
        difficulty_scheme=parse_enum(
            DifficultyScheme, data.get("difficulty_scheme", "unknown"), "difficulty_scheme"
        ),
        total_problems=data.get("total_problems", 0),
        problems_solved=data.get("problems_solved", 0)
    )
    return jsonify(serialize(source)), 201


@app.route("/sources/<int:source_id>", methods=["PATCH"])
def update_source(source_id):
    db = get_db()
    data = body()
    source = sc.update_source(
        db=db,
        source_id=source_id,
        new_name=data.get("new_name"),
        new_topic_id=data.get("new_topic_id"),
        new_track=parse_enum(Track, data.get("new_track"), "new_track"),
        new_rated_difficulty=parse_enum(
            RatedDifficulty, data.get("new_rated_difficulty"), "new_rated_difficulty"
        ),
        new_difficulty_scheme=parse_enum(
            DifficultyScheme, data.get("new_difficulty_scheme"), "new_difficulty_scheme"
        ),
        new_total_problems=data.get("new_total_problems"),
        new_problems_solved=data.get("new_problems_solved")
    )
    return jsonify(serialize(source))


@app.route("/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    db = get_db()
    source = sc.soft_delete_source(db=db, source_id=source_id)
    return jsonify(serialize(source))


# ==========================================
# SOURCE EXERCISES
# ==========================================

@app.route("/sources/<int:source_id>/exercises", methods=["GET"])
def list_exercises(source_id):
    db = get_db()
    exercises = db.query(SourceExercise).filter(
        SourceExercise.source_id == source_id,
        SourceExercise.is_active == True  # noqa: E712
    ).all()
    return jsonify(serialize_many(exercises))


@app.route("/sources/<int:source_id>/exercises", methods=["POST"])
def create_exercise(source_id):
    db = get_db()
    data = body()
    exercise = sc.create_source_exercise(
        db=db,
        source_id=source_id,
        exercise_number=data.get("exercise_number"),
        problems_in_exercise=data.get("problems_in_exercise", 0),
        problems_solved=data.get("problems_solved", 0)
    )
    return jsonify(serialize(exercise)), 201


@app.route("/exercises/<int:exercise_id>", methods=["PATCH"])
def update_exercise(exercise_id):
    db = get_db()
    data = body()
    exercise = sc.update_source_exercise(
        db=db,
        exercise_id=exercise_id,
        new_source_id=data.get("new_source_id"),
        new_exercise_number=data.get("new_exercise_number"),
        new_problems_in_exercise=data.get("new_problems_in_exercise"),
        new_problems_solved=data.get("new_problems_solved")
    )
    return jsonify(serialize(exercise))


@app.route("/exercises/<int:exercise_id>", methods=["DELETE"])
def delete_exercise(exercise_id):
    db = get_db()
    exercise = sc.soft_delete_exercise(db=db, exercise_id=exercise_id)
    return jsonify(serialize(exercise))


# ==========================================
# SESSIONS
# ==========================================

@app.route("/sessions/<int:session_id>", methods=["GET"])
def get_session(session_id):
    """Session status snapshot: the session itself, its currently-open
    question (if any), and every question logged in it so far."""
    db = get_db()
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if session is None:
        raise ValueError(f"Session {session_id} not found.")

    questions = db.query(Question).filter(Question.session_id == session_id) \
        .order_by(Question.position_in_session).all()

    return jsonify({
        "session": serialize(session),
        "current_question": serialize(get_open_question(db, session_id)),
        "questions": serialize_many(questions)
    })


@app.route("/sessions", methods=["POST"])
def start_session():
    db = get_db()
    data = body()
    session = ss.start_session(
        db=db,
        topic_id=data.get("topic_id"),
        source_id=data.get("source_id"),
        track=parse_enum(Track, data.get("track"), "track"),
        starting_question_number=data.get("starting_question_number", 1),
        subtopic_id=data.get("subtopic_id"),
        exercise_id=data.get("exercise_id"),
        batch_size=data.get("batch_size", 10)
    )
    return jsonify({
        "session": serialize(session),
        "current_question": serialize(get_open_question(db, session.session_id))
    }), 201


@app.route("/sessions/<int:session_id>/pause", methods=["POST"])
def pause_session(session_id):
    db = get_db()
    session = ss.pause_session(db=db, session_id=session_id)
    return jsonify(serialize(session))


@app.route("/sessions/<int:session_id>/resume", methods=["POST"])
def resume_session(session_id):
    db = get_db()
    session = ss.resume_session(db=db, session_id=session_id)
    return jsonify(serialize(session))


@app.route("/sessions/<int:session_id>/questions/complete", methods=["POST"])
def complete_question(session_id):
    db = get_db()
    data = body()
    question, batch_complete = ss.complete_question(
        db=db,
        session_id=session_id,
        subjective_difficulty=parse_enum(
            SubjectiveDifficulty, data.get("subjective_difficulty"), "subjective_difficulty"
        ),
        confidence_rating=parse_enum(
            ConfidenceRating, data.get("confidence_rating"), "confidence_rating"
        ),
        photo_path=data.get("photo_path")
    )
    return jsonify({
        "completed_question": serialize(question),
        "batch_complete": batch_complete,
        "current_question": serialize(get_open_question(db, session_id))
    })


@app.route("/sessions/<int:session_id>/grade", methods=["POST"])
def grade_batch(session_id):
    db = get_db()
    data = body()
    raw_results = data.get("results", [])

    parsed_results = []
    for r in raw_results:
        parsed_results.append({
            "question_id": r.get("question_id"),
            "correctness": parse_enum(Correctness, r.get("correctness"), "correctness"),
            "error_type": parse_enum(ErrorType, r.get("error_type"), "error_type")
        })

    graded = ss.grade_batch(db=db, session_id=session_id, results=parsed_results)
    return jsonify({
        "graded_questions": serialize_many(graded),
        "current_question": serialize(get_open_question(db, session_id))
    })


@app.route("/sessions/<int:session_id>/end", methods=["POST"])
def end_session(session_id):
    db = get_db()
    data = body()
    result = ss.end_session(
        db=db,
        session_id=session_id,
        subjective_difficulty=parse_enum(
            SubjectiveDifficulty, data.get("subjective_difficulty"), "subjective_difficulty"
        ),
        confidence_rating=parse_enum(
            ConfidenceRating, data.get("confidence_rating"), "confidence_rating"
        ),
        photo_path=data.get("photo_path")
    )
    return jsonify({
        "session": serialize(result["session"]),
        "ungraded_questions": serialize_many(result["ungraded_questions"])
    })


if __name__ == "__main__":
    # Reachable from iPad/phone over home wifi via local IP (per DECISIONS.md) —
    # 0.0.0.0 binds to all interfaces, not just localhost.
    app.run(host="0.0.0.0", port=8000, debug=True)