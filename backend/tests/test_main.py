import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as main_module
from app.models import Base


# ==============================================
# Fixture — isolated in-memory DB per test, with
# app.main.SessionLocal monkeypatched to point at
# it, so no test ever touches the real dawn.db.
# ==============================================

@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestSessionLocal)

    main_module.app.config["TESTING"] = True
    with main_module.app.test_client() as test_client:
        yield test_client

    Base.metadata.drop_all(engine)


# ==============================================
# Helpers — build up hierarchy/source fixtures
# through the API itself, since this file tests
# the HTTP layer end to end, not the services.
# ==============================================

def _create_subject(client, name="Physics"):
    resp = client.post("/subjects", json={"subject_name": name})
    assert resp.status_code == 201
    return resp.get_json()


def _create_topic(client, subject_id, name="Rotational Dynamics", track="JEE"):
    resp = client.post("/topics", json={
        "topic_name": name, "subject_id": subject_id, "track": track
    })
    assert resp.status_code == 201
    return resp.get_json()


def _create_source(client, topic_id, total_problems=50, name="HC Verma Part 1"):
    resp = client.post("/sources", json={
        "book_name": name,
        "topic_id": topic_id,
        "track": "JEE",
        "total_problems": total_problems
    })
    assert resp.status_code == 201
    return resp.get_json()


def _create_exercise(client, source_id, problems_in_exercise=3, number="Exercise 1"):
    resp = client.post(f"/sources/{source_id}/exercises", json={
        "exercise_number": number, "problems_in_exercise": problems_in_exercise
    })
    assert resp.status_code == 201
    return resp.get_json()


def _topic_and_source(client, total_problems=50):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])
    source = _create_source(client, topic["topic_id"], total_problems=total_problems)
    return topic, source


# ==============================================
# 1. Subjects
# ==============================================

def test_create_and_list_subjects(client):
    subject = _create_subject(client)
    assert subject["subject_name"] == "Physics"
    assert subject["is_active"] is True

    listed = client.get("/subjects").get_json()
    assert any(s["subject_id"] == subject["subject_id"] for s in listed)


def test_update_and_delete_subject(client):
    subject = _create_subject(client)

    updated = client.patch(f"/subjects/{subject['subject_id']}", json={"new_name": "Chemistry"})
    assert updated.status_code == 200
    assert updated.get_json()["subject_name"] == "Chemistry"

    deleted = client.delete(f"/subjects/{subject['subject_id']}")
    assert deleted.status_code == 200
    assert deleted.get_json()["is_active"] is False

    listed = client.get("/subjects").get_json()
    assert all(s["subject_id"] != subject["subject_id"] for s in listed)


# ==============================================
# 2. Topics
# ==============================================

def test_create_topic_and_filter_by_subject(client):
    subject_a = _create_subject(client, "Physics")
    subject_b = _create_subject(client, "Chemistry")
    topic_a = _create_topic(client, subject_a["subject_id"])
    _create_topic(client, subject_b["subject_id"], name="Chemical Bonding")

    listed = client.get(f"/topics?subject_id={subject_a['subject_id']}").get_json()
    assert len(listed) == 1
    assert listed[0]["topic_id"] == topic_a["topic_id"]


def test_update_topic_partial_fields_leave_others_untouched(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"], track="JEE")

    updated = client.patch(f"/topics/{topic['topic_id']}", json={"new_name": "Rotational Motion"})
    assert updated.status_code == 200
    data = updated.get_json()
    assert data["topic_name"] == "Rotational Motion"
    assert data["track"] == "JEE"  # untouched since new_track wasn't sent


def test_delete_topic(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])

    deleted = client.delete(f"/topics/{topic['topic_id']}")
    assert deleted.status_code == 200
    assert deleted.get_json()["is_active"] is False


def test_merge_topics_via_api(client):
    subject = _create_subject(client)
    source_topic = _create_topic(client, subject["subject_id"], name="Rotational Motion")
    target_topic = _create_topic(client, subject["subject_id"], name="Rotational Dynamics")

    resp = client.post("/topics/merge", json={
        "source_topic_id": source_topic["topic_id"],
        "target_topic_id": target_topic["topic_id"]
    })
    assert resp.status_code == 200
    assert resp.get_json()["topic_id"] == target_topic["topic_id"]


def test_merge_topic_into_itself_returns_400(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])

    resp = client.post("/topics/merge", json={
        "source_topic_id": topic["topic_id"],
        "target_topic_id": topic["topic_id"]
    })
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ==============================================
# 3. Subtopics
# ==============================================

def test_create_subtopic_and_filter_by_topic(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])
    resp = client.post("/subtopics", json={
        "subtopic_name": "Moment of Inertia", "topic_id": topic["topic_id"]
    })
    assert resp.status_code == 201
    subtopic = resp.get_json()

    listed = client.get(f"/subtopics?topic_id={topic['topic_id']}").get_json()
    assert len(listed) == 1
    assert listed[0]["subtopic_id"] == subtopic["subtopic_id"]


def test_update_and_delete_subtopic(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])
    subtopic = client.post("/subtopics", json={
        "subtopic_name": "Moment of Inertia", "topic_id": topic["topic_id"]
    }).get_json()

    updated = client.patch(f"/subtopics/{subtopic['subtopic_id']}", json={"new_name": "Torque"})
    assert updated.get_json()["subtopic_name"] == "Torque"

    deleted = client.delete(f"/subtopics/{subtopic['subtopic_id']}")
    assert deleted.get_json()["is_active"] is False


# ==============================================
# 4. Sources & exercises
# ==============================================

def test_create_source_applies_defaults(client):
    subject = _create_subject(client)
    topic = _create_topic(client, subject["subject_id"])

    resp = client.post("/sources", json={
        "book_name": "HC Verma Part 1", "topic_id": topic["topic_id"], "track": "JEE"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["rated_difficulty"] == "Unrated"
    assert data["difficulty_scheme"] == "unknown"
    assert data["total_problems"] == 0
    assert data["problems_solved"] == 0


def test_list_sources_filtered_by_topic(client):
    topic, source = _topic_and_source(client)
    listed = client.get(f"/sources?topic_id={topic['topic_id']}").get_json()
    assert len(listed) == 1
    assert listed[0]["source_id"] == source["source_id"]


def test_update_and_delete_source(client):
    _, source = _topic_and_source(client)

    updated = client.patch(f"/sources/{source['source_id']}", json={"new_rated_difficulty": "Hard"})
    assert updated.get_json()["rated_difficulty"] == "Hard"

    deleted = client.delete(f"/sources/{source['source_id']}")
    assert deleted.get_json()["is_active"] is False


def test_create_and_list_exercises(client):
    _, source = _topic_and_source(client)
    exercise = _create_exercise(client, source["source_id"])

    listed = client.get(f"/sources/{source['source_id']}/exercises").get_json()
    assert len(listed) == 1
    assert listed[0]["exercise_id"] == exercise["exercise_id"]


def test_update_and_delete_exercise(client):
    _, source = _topic_and_source(client)
    exercise = _create_exercise(client, source["source_id"])

    updated = client.patch(f"/exercises/{exercise['exercise_id']}", json={
        "new_problems_in_exercise": 10
    })
    assert updated.get_json()["problems_in_exercise"] == 10

    deleted = client.delete(f"/exercises/{exercise['exercise_id']}")
    assert deleted.get_json()["is_active"] is False


# ==============================================
# 5. Sessions — full lifecycle through the API
# ==============================================

def test_start_session_returns_session_and_open_question(client):
    topic, source = _topic_and_source(client)

    resp = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE", "batch_size": 5
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["session"]["is_paused"] is False
    assert data["current_question"]["position_in_session"] == 1
    assert data["current_question"]["timestamp"] is None


def test_batch_closes_at_batch_size_via_api(client):
    topic, source = _topic_and_source(client, total_problems=100)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE", "batch_size": 2
    }).get_json()["session"]

    first = client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Easy"
    }).get_json()
    assert first["batch_complete"] is False
    assert first["current_question"]["position_in_session"] == 2

    second = client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Hard"
    }).get_json()
    assert second["batch_complete"] is True
    assert second["current_question"] is None


def test_batch_closes_early_when_exercise_exhausted_via_api(client):
    topic, source = _topic_and_source(client, total_problems=100)
    exercise = _create_exercise(client, source["source_id"], problems_in_exercise=1)

    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"],
        "exercise_id": exercise["exercise_id"], "track": "JEE", "batch_size": 10
    }).get_json()["session"]

    result = client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Medium"
    }).get_json()
    assert result["batch_complete"] is True  # exhaustion, not batch_size, closed it


def test_full_session_lifecycle_via_api(client):
    topic, source = _topic_and_source(client, total_problems=100)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE", "batch_size": 2
    }).get_json()["session"]
    session_id = session["session_id"]

    q1 = client.post(f"/sessions/{session_id}/questions/complete", json={
        "subjective_difficulty": "Easy"
    }).get_json()["completed_question"]
    q2 = client.post(f"/sessions/{session_id}/questions/complete", json={
        "subjective_difficulty": "Hard"
    }).get_json()["completed_question"]

    graded = client.post(f"/sessions/{session_id}/grade", json={
        "results": [
            {"question_id": q1["question_id"], "correctness": "Correct", "error_type": "Nil"},
            {"question_id": q2["question_id"], "correctness": "Incorrect", "error_type": "Silly"},
        ]
    })
    assert graded.status_code == 200
    graded_data = graded.get_json()
    assert {g["correctness"] for g in graded_data["graded_questions"]} == {"Correct", "Incorrect"}
    # Source has plenty of problems left -> grading should have opened question 3
    assert graded_data["current_question"]["position_in_session"] == 3

    status = client.get(f"/sessions/{session_id}").get_json()
    assert len(status["questions"]) == 3
    assert status["current_question"]["position_in_session"] == 3

    # grade_batch opened question 3 (source has plenty of problems left); ending
    # the session completes that question but doesn't grade it — so it's the
    # one ungraded question left, even though q1/q2 were graded.
    ended = client.post(f"/sessions/{session_id}/end", json={"subjective_difficulty": "Medium"})
    assert ended.status_code == 200
    ended_data = ended.get_json()
    assert ended_data["session"]["end_time"] is not None
    assert len(ended_data["ungraded_questions"]) == 1
    assert ended_data["ungraded_questions"][0]["position_in_session"] == 3


def test_end_session_reports_ungraded_questions(client):
    topic, source = _topic_and_source(client, total_problems=100)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE"
    }).get_json()["session"]

    client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Easy"
    })  # completed but never graded; opens question 2

    ended = client.post(f"/sessions/{session['session_id']}/end", json={
        "subjective_difficulty": "Medium"
    }).get_json()

    assert len(ended["ungraded_questions"]) == 2  # both q1 and q2 are Pending


def test_pause_blocks_question_completion(client):
    topic, source = _topic_and_source(client)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE"
    }).get_json()["session"]

    paused = client.post(f"/sessions/{session['session_id']}/pause")
    assert paused.status_code == 200
    assert paused.get_json()["is_paused"] is True

    blocked = client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Easy"
    })
    assert blocked.status_code == 400
    assert "paused" in blocked.get_json()["error"]

    resumed = client.post(f"/sessions/{session['session_id']}/resume")
    assert resumed.status_code == 200
    assert resumed.get_json()["is_paused"] is False

    unblocked = client.post(f"/sessions/{session['session_id']}/questions/complete", json={
        "subjective_difficulty": "Easy"
    })
    assert unblocked.status_code == 200


def test_end_session_without_difficulty_when_open_returns_400(client):
    topic, source = _topic_and_source(client)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE"
    }).get_json()["session"]

    resp = client.post(f"/sessions/{session['session_id']}/end", json={})
    assert resp.status_code == 400
    assert "subjective_difficulty is required" in resp.get_json()["error"]


# ==============================================
# 6. Error handling
# ==============================================

def test_invalid_enum_value_returns_400_with_helpful_message(client):
    subject = _create_subject(client)
    resp = client.post("/topics", json={
        "topic_name": "Something", "subject_id": subject["subject_id"], "track": "Nonsense"
    })
    assert resp.status_code == 400
    body = resp.get_json()
    assert "Nonsense" in body["error"]
    assert "JEE" in body["error"]  # lists the valid options


def test_unknown_session_id_returns_400(client):
    resp = client.get("/sessions/999999")
    assert resp.status_code == 400
    assert "not found" in resp.get_json()["error"]

    resp = client.post("/sessions/999999/pause")
    assert resp.status_code == 400
    assert "not found" in resp.get_json()["error"]


def test_grade_batch_unknown_question_returns_400(client):
    topic, source = _topic_and_source(client)
    session = client.post("/sessions", json={
        "topic_id": topic["topic_id"], "source_id": source["source_id"], "track": "JEE"
    }).get_json()["session"]

    resp = client.post(f"/sessions/{session['session_id']}/grade", json={
        "results": [{"question_id": 999999, "correctness": "Correct", "error_type": "Nil"}]
    })
    assert resp.status_code == 400
    assert "not found" in resp.get_json()["error"]