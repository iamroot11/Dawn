from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import get_db
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # insecure right now, tighten for future use
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/topics") # When a request is sent to topics
def add_topic(payload: TopicCreate, db: Session = Depends(get_db)):
    
    # Find the existing subject, or create subject if it doesn't exist yet
    subject = db.query(Subject).filter_by(subject_name = payload.subject_name).first()
    if subject is None: # Doesn't exist
        subject = Subject(subject_name = payload.subject_name)
        db.add(subject)
    
    try:
        track = Track(payload.track)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid track: {payload.track}")
    
    # Add the topic
    topic = Topic(topic_name = payload.topic_name, subject = subject, track = Track(payload.track))
    db.add(topic)
    
    if payload.subtopic_name: # Subtopic also exists
        subtopic = Subtopic(subtopic_name = payload.subtopic_name, topic = topic)
        db.add(subtopic)
    
    db.commit() # Commit all changes added to the DB
    return {"status": "added", "topic": payload.topic_name}