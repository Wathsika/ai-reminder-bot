import os
from google import genai
from app.database import SessionLocal, Reminder, Timetable 
from datetime import datetime, timedelta

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- TOOLS FOR GEMINI ---

def add_reminder(user_id: str, task: str, time_str: str):
    """Adds a new reminder. time_str format: 'YYYY-MM-DD HH:MM'"""
    db = SessionLocal()
    new_task = Reminder(
        user_id=user_id, 
        task=task, 
        remind_at=datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    )
    db.add(new_task)
    db.commit()
    db.close()
    return f"✅ Set reminder: {task} for {time_str}"

def add_timetable(user_id: str, day: str, subject: str, time: str):
    """Saves a recurring campus timetable entry."""
    db = SessionLocal()
    entry = Timetable(user_id=user_id, day=day, subject=subject, time=time)
    db.add(entry)
    db.commit()
    db.close()
    return f"📚 Saved to timetable: {subject} on {day} at {time}"

def complete_task(user_id: str, task_name: str):
    """Marks a task as finished and deletes it."""
    db = SessionLocal()
    task = db.query(Reminder).filter(
        Reminder.user_id == user_id, 
        Reminder.task.ilike(f"%{task_name}%")
    ).first()
    if task:
        db.delete(task)
        db.commit()
        db.close()
        return f"🎉 Great! I've cleared '{task_name}' from your list."
    return "❌ I couldn't find that task in your list."

# --- AGENT CONFIG ---

tools = [add_reminder, add_timetable, complete_task]
model_id = "gemini-2.5-flash" # Can be updated via chat command later

def get_ai_response(user_input: str, user_id: str):
    # We include the current time so Gemini knows what "4 PM" means today
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M, %A")
    prompt = f"System Time: {current_time}. User ID: {user_id}. {user_input}"
    
    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config={'tools': tools} # Enable automatic tool calling
    )
    return response.text