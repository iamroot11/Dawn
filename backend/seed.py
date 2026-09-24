from app.database import SessionLocal
from app.models import Subject, Topic, Subtopic, Track

db = SessionLocal()

physics = Subject(subject_name="Physics")
mechanics = Topic(topic_name="Rotational Dynamics", subject=physics, track=Track.JEE)
moi = Subtopic(subtopic_name="Moment of Inertia", topic=mechanics)

db.add_all([physics, mechanics, moi])
db.commit()
db.close()

print("Seeded successfully.")