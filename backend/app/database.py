from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///dawn.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# This is so that we don't need to open or close the db in every FastAPI endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()