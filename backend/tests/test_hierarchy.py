import pytest
from app.services import hierarchy as hc
from app.models import Subject, Topic, Subtopic, Track

# ==============================================
# 1. Creation Test
# ==============================================

def test_create_hierarchy_success(db):
    """"
    Tests for creating Subject -> Topic -> Subtopic
    """ 
    physics = hc.create_subject(db = db, subject_name = "Physics")
    mechanics = hc.create_topic(db = db, topic_name = "Rotational Dynamics", subject_id = physics.subject_id, track = Track.JEE)
    moi = hc.create_subtopic(db = db, subtopic_name = "Moment of Inertia", topic_id = mechanics.topic_id)
    
    # Assert subject
    saved_subject = db.query(Subject).filter_by(subject_name="Physics").first()
    assert saved_subject is not None
    assert saved_subject.is_active is True
    
    # Assert Topic
    saved_topic = db.query(Topic).filter_by(topic_name="Rotational Dynamics").first()
    assert saved_topic is not None
    assert saved_topic.subject.subject_name == "Physics"
    assert saved_topic.track == Track.JEE
    
    # Assert Subtopic
    saved_subtopic = db.query(Subtopic).filter_by(subtopic_name="Moment of Inertia").first()
    assert saved_subtopic is not None
    assert saved_subtopic.topic.topic_name == "Rotational Dynamics"

# ==============================================
# 2. Updates & Remaining Test
# ==============================================

def test_update_and_soft_delete_topic(db):
    """Test renaming a topic and soft deleting it."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    topic = hc.create_topic(db=db, topic_name="Rotational Motion", subject_id=physics.subject_id, track = Track.JEE)

    # Test Rename
    updated_topic = hc.update_topic(db=db, topic_id=topic.topic_id, new_name="Rotational Dynamics")
    assert updated_topic.topic_name == "Rotational Dynamics"

    # Test Soft Delete
    deleted_topic = hc.soft_delete_topic(db=db, topic_id=topic.topic_id)
    assert deleted_topic.is_active is False
    
    # Ensure it's still in the DB (not hard deleted)
    db_record = db.query(Topic).filter_by(topic_id=topic.topic_id).first()
    assert db_record is not None
    assert db_record.is_active is False

# ==============================================
# 3. Topic Merge Tests
# ==============================================

def test_merge_topics_relinks_subtopics(db):
    """Test that merging Topic A into Topic B correctly re-parents subtopics and drops Topic A."""
    physics = hc.create_subject(db=db, subject_name="Physics")

    # Source topic (duplicate) and target topic
    source_topic = hc.create_topic(db=db, topic_name="Rotational Motion", subject_id=physics.subject_id, track = Track.JEE)
    target_topic = hc.create_topic(db=db, topic_name="Rotational Dynamics", subject_id=physics.subject_id, track = Track.JEE)

    # Subtopic under source topic
    sub = hc.create_subtopic(db=db, subtopic_name="Moment of Inertia", topic_id=source_topic.topic_id)

    # Execute Merge
    merged_topic = hc.merge_topic(db=db, source_topic_id=source_topic.topic_id, target_topic_id=target_topic.topic_id)

    # Assert Source Topic was hard deleted
    old_topic_query = db.query(Topic).filter_by(topic_id=source_topic.topic_id).first()
    assert old_topic_query is None

    # Assert Subtopic was re-parented to Target Topic
    db.refresh(sub)
    assert sub.topic_id == target_topic.topic_id
    assert sub.topic.topic_name == "Rotational Dynamics"

def test_merge_topic_into_itself_raises_error(db):
    """Edge Case Test: Attempting to merge a topic into itself should fail."""
    physics = hc.create_subject(db=db, subject_name="Physics")
    topic = hc.create_topic(db=db, topic_name="Mechanics", subject_id=physics.subject_id, track = Track.JEE)

    with pytest.raises(ValueError, match="Cannot merge a topic into itself"):
        hc.merge_topic(db=db, source_topic_id=topic.topic_id, target_topic_id=topic.topic_id)
