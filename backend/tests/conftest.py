import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

@pytest.fixture(scope="function")
def db():
    """
    Creates an in-memory SQLite database for every test function,
    instantiates tables, yields a session, and drops everything after.
    """
    # Use in-memory SQLite for fast, isolated tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Create all tables in memory from Declarative Base
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)