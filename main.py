from fastapi import FastAPI
from app.database import SessionLocal
from app.models import Subject, Topic, Subtopic, Track

# For the pydantic models
from pydantic import BaseModel

# Our Pydantic model: Basically defines what kind of data is acceptable
class TopicCreate(BaseModel):
    subject_name: str
    topic_name: str
    track: str
    subtopic_name: str | None = None # Meaning this is optional

app = FastAPI()

@app.post("/topics") # When a request is sent to topics
def add_topic(payload: TopicCreate):
    db = SessionLocal() # Create a session for the database
    
    # Find the existing subject, or create subject if it doesn't exist yet
    subject = db.query(Subject).filter_by(subject_name = payload.subject_name).first()
    if subject is None: # Doesn't exist
        subject = Subject(subject_name = payload.subject_name)
        db.add(subject)
    
    # Add the topic
    topic = Topic(topic_name = payload.topic_name, subject = subject, track = Track(payload.track))
    db.add(topic)
    
    if payload.subtopic_name: # Subtopic also exists
        subtopic = Subtopic(subtopic_name = payload.subtopic_name, topic = topic)
        db.add(subtopic)
    
    db.commit() # Commit all changes added to the DB
    db.close()
    return {"status": "added", "topic": payload.topic_name}
