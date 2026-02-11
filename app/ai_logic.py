import os
from google import genai
from app.database import SessionLocal, Reminder, Timetable
from datetime import datetime
import pytz

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- TOOLS GEMINI CAN USE ---

def add_reminder(user_id: str, task: str, time_str: str):
    """Adds a reminder. time_str format: 'YYYY-MM-DD HH:MM'"""
    db = SessionLocal()
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        new_task = Reminder(user_id=user_id, task=task, remind_at=dt)
        db.add(new_task)
        db.commit()
        return f"✅ OK! I'll remind you to '{task}' at {time_str}."
    except Exception as e:
        return f"❌ Error saving reminder: {e}"
    finally:
        db.close()

def add_timetable(user_id: str, day: str, subject: str, time: str):
    """Saves a campus timetable entry."""
    db = SessionLocal()
    entry = Timetable(user_id=user_id, day=day, subject=subject, time=time)
    db.add(entry)
    db.commit()
    db.close()
    return f"📚 Saved: {subject} on {day} at {time}."

def complete_task(user_id: str, task_name: str):
    """Clears a task when finished."""
    db = SessionLocal()
    task = db.query(Reminder).filter(Reminder.user_id == user_id, Reminder.task.ilike(f"%{task_name}%")).first()
    if task:
        db.delete(task)
        db.commit()
        db.close()
        return f"🎉 Task '{task_name}' completed and removed!"
    db.close()
    return f"❌ Couldn't find task '{task_name}'."

# --- LOGIC ---

def get_ai_response(user_input: str, user_id: str):
    # Set your timezone!
    tz = pytz.timezone('Asia/Colombo')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M, %A")
    
    # System Instructions for the Agent
    sys_msg = (
        f"Current Time: {now}. You are a proactive assistant. "
        "Use tools to manage reminders and timetables. "
        "When asked to remind, use 'add_reminder'. When a task is done, use 'complete_task'."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_input,
        config={
            "system_instruction": sys_msg,
            "tools": [add_reminder, add_timetable, complete_task]
        }
    )
    return response.text