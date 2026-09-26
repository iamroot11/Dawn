# Handles Creating Subjects, Topics and Subtopics
from typing import Optional, List
from sqlalchemy.orm import Session as DBSession
from app.models import Assignment, BoardSyllabus, Question, Source, Subject, Topic, Subtopic, Track, Session


# ==========================================
# SUBJECTS
# ==========================================

def create_subject(db: DBSession, subject_name: str) -> Subject:
    subject = Subject(subject_name = subject_name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

def update_subject(db: DBSession, subject_id: int, new_name: str) -> Subject:
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise ValueError(f"Subject {subject_id} not found.")
    subject.subject_name = new_name
    db.commit()
    db.refresh(subject)
    return subject

def soft_delete_subject(db: DBSession, subject_id: int) -> Subject:
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        raise ValueError(f"Subject {subject_id} not found.")
    subject.is_active = False
    db.commit()
    db.refresh(subject)
    return subject

# ==========================================
# TOPICS
# ==========================================

def create_topic(db: DBSession, topic_name: str, subject_id: int, track: Track) -> Topic:
    topic = Topic(topic_name = topic_name, subject_id = subject_id, track = track)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic

def update_topic(
    db: DBSession,
    topic_id: int,
    new_name: Optional[str] = None,
    new_subject_id: Optional[int] = None,
    new_track: Optional[Track] = None
) ->  Topic:
    topic = db.query(Topic).filter(Topic.topic_id == topic_id).first()
    if not topic:
        raise ValueError(f"Topic {topic_id} not found")
    if new_name is not None:
        topic.topic_name = new_name
    if new_subject_id is not None:
        topic.subject_id = new_subject_id
    if new_track is not None:
        topic.track = new_track    

    db.commit()
    db.refresh(topic)
    return topic

def soft_delete_topic(db: DBSession, topic_id: int) -> Topic:
    """Soft deletes a topic and all its subtopics, preserving questions, sessions, and analytics history."""
    topic = db.query(Topic).filter(Topic.topic_id == topic_id).first()
    if not topic:
        raise ValueError(f"Topic {topic_id} not found.")
    
    topic.is_active = False
    
    # Deleting all the child subtopics
    subtopics = db.query(Subtopic).filter(Subtopic.topic_id == topic_id).all()
    for sub in subtopics:
        sub.is_active = False
        
    db.commit()
    db.refresh(topic)
    return topic

def merge_topic(db: DBSession, source_topic_id: int, target_topic_id: int) -> Topic:
    """
    Safely merges source_topic into target_topic by re-linking all historical records
    (Questions, Sessions, Sources, Assignments, Subtopics) before removing the source topic.
    """
    
    if source_topic_id == target_topic_id:
        raise ValueError("Cannot merge a topic into itself.")
    
    source_topic = db.query(Topic).filter(Topic.topic_id == source_topic_id).first()
    target_topic = db.query(Topic).filter(Topic.topic_id == target_topic_id).first()
    
    if not source_topic or not target_topic:
        raise ValueError("One or both topics do not exist.")
    
    # Re-link all child topics
    db.query(Subtopic).filter(Subtopic.topic_id == source_topic_id).update({Subtopic.topic_id: target_topic_id})
    db.query(Question).filter(Question.topic_id == source_topic_id).update({Question.topic_id: target_topic_id})
    db.query(Session).filter(Session.topic_id == source_topic_id).update({Session.topic_id: target_topic_id})
    db.query(Source).filter(Source.topic_id == source_topic_id).update({Source.topic_id: target_topic_id})
    db.query(Assignment).filter(Assignment.topic_id == source_topic_id).update({Assignment.topic_id: target_topic_id})
    db.query(BoardSyllabus).filter(BoardSyllabus.topic_id == source_topic_id).update({BoardSyllabus.topic_id: target_topic_id})
    
    # Hard delete source topic now that all dependencies have been re-routed
    db.delete(source_topic)
    db.commit()
    db.refresh(target_topic)
    return target_topic

# ==========================================
# SUBTOPICS
# ==========================================
def create_subtopic(db: Session, subtopic_name: str, topic_id: int) -> Subtopic:
    subtopic = Subtopic(subtopic_name=subtopic_name, topic_id=topic_id, is_active=True)
    db.add(subtopic)
    db.commit()
    db.refresh(subtopic)
    return subtopic

def update_subtopic(
    db: Session, 
    subtopic_id: int, 
    new_name: Optional[str] = None, 
    new_topic_id: Optional[int] = None
) -> Subtopic:
    subtopic = db.query(Subtopic).filter(Subtopic.subtopic_id == subtopic_id).first()
    if not subtopic:
        raise ValueError(f"Subtopic {subtopic_id} not found.")
    
    if new_name is not None:
        subtopic.subtopic_name = new_name
    if new_topic_id is not None:
        subtopic.topic_id = new_topic_id
        
    db.commit()
    db.refresh(subtopic)
    return subtopic

def soft_delete_subtopic(db: Session, subtopic_id: int) -> Subtopic:
    subtopic = db.query(Subtopic).filter(Subtopic.subtopic_id == subtopic_id).first()
    if not subtopic:
        raise ValueError(f"Subtopic {subtopic_id} not found.")
    
    subtopic.is_active = False
    db.commit()
    db.refresh(subtopic)
    return subtopic