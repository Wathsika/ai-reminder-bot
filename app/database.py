import os
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from datetime import datetime

# DATABASE_URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    # Added index=True here to make user-specific lookups fast
    user_id = Column(String, index=True) 
    task = Column(String)
    remind_at = Column(DateTime)
    status = Column(String, default="PENDING") # PENDING, NAGGING

class Timetable(Base):
    __tablename__ = "timetable"
    
    id = Column(Integer, primary_key=True, index=True)
    # Added index=True here too
    user_id = Column(String, index=True)
    day = Column(String) # e.g., "Monday"
    subject = Column(String)
    time = Column(String) # e.g., "10:30 AM"

# DevOps Robustness: Wait for DB to be ready before creating tables
def init_db():
    print("Connecting to database...")
    retries = 5
    while retries > 0:
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database connected and tables created successfully.")
            return # Exit function once successful
        except OperationalError as e:
            print(f"⏳ Database not ready yet ({e}). Retrying in 2 seconds... ({retries} retries left)")
            time.sleep(2)
            retries -= 1
    
    print("❌ Could not connect to the database. Exiting.")
    raise SystemExit(1)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    role = Column(String)  # "user" or "model"
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)