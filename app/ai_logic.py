import os
from google import genai
from google.genai import types # Added for tool configuration
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
    try:
        entry = Timetable(user_id=user_id, day=day, subject=subject, time=time)
        db.add(entry)
        db.commit()
        return f"📚 Saved: {subject} on {day} at {time}."
    finally:
        db.close()

def complete_task(user_id: str, task_id: int):
    """Clears a task by its ID."""
    db = SessionLocal()
    try:
        task = db.query(Reminder).filter(Reminder.id == task_id, Reminder.user_id == user_id).first()
        if task:
            db.delete(task)
            db.commit()
            return f"🎉 Task with ID {task_id} completed and removed!"
        return f"❌ Couldn't find task with ID {task_id}."
    finally:
        db.close()

def get_reminders(user_id: str):
    """Gets all reminders for a user."""
    db = SessionLocal()
    try:
        tasks = db.query(Reminder).filter(Reminder.user_id == user_id).all()
        if not tasks:
            return "You have no pending reminders."
        
        response = "Your reminders:\n"
        for task in tasks:
            response += f"  - ID: {task.id}, Task: {task.task}, Due: {task.remind_at}\n"
        return response
    finally:
        db.close()

# --- LOGIC ---

def get_ai_response(user_input: str, user_id: str):
    # Set your timezone!
    tz = pytz.timezone('Asia/Colombo')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M, %A")
    
    sys_msg = (
        f"Current Time: {now}. You are a proactive assistant. "
        f"The current user's ID is {user_id}. "
        "Use tools to manage reminders and timetables. "
        "IMPORTANT: You already have the user's ID. NEVER ask the user for their ID. "
        "If you detect a typo, correct it silently in the tool call. "
        "When asked to remind, use 'add_reminder'. To see tasks, use 'get_reminders'."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=user_input,
        config=types.GenerateContentConfig(
            system_instruction=sys_msg,
            tools=[add_reminder, add_timetable, complete_task, get_reminders],
            # FIXED LINE BELOW:
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
        )
    )
    
    return response.text