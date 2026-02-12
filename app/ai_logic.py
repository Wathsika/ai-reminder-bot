import os
from google import genai
from google.genai import types # Added for tool configuration
from app.database import SessionLocal, Reminder, Timetable, ChatHistory
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
    db = SessionLocal()
    tz = pytz.timezone('Asia/Colombo')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M, %A")
    
    # 1. Fetch last 10 messages from DB for context
    history_records = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    
    # Reverse them to get chronological order
    history_records.reverse()

    # 2. Format history for Gemini SDK
    # Gemini expects: [{'role': 'user', 'parts': ['...']}, {'role': 'model', 'parts': ['...']}]
    formatted_history = []
    for record in history_records:
        formatted_history.append({"role": record.role, "parts": [record.content]})

    sys_msg = (
        f"Current Time: {now}. You are a proactive assistant. "
        f"The current user's ID is {user_id}. "
        "Use tools to manage reminders. If the user says 'Remind it in X minutes', "
        "look at the chat history to see what 'it' refers to (the last thing discussed)."
    )

    # 3. Call Gemini with history + the new message
    try:
        # Note: If you are using gemini-2.0, change the model name accordingly
        # We use generate_content with the full history list
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Use a stable model name
            contents=formatted_history + [{"role": "user", "parts": [user_input]}],
            config=types.GenerateContentConfig(
                system_instruction=sys_msg,
                tools=[add_reminder, add_timetable, complete_task, get_reminders],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
        ai_text = response.text

        # 4. Save this interaction to history
        new_user_msg = ChatHistory(user_id=user_id, role="user", content=user_input)
        new_ai_msg = ChatHistory(user_id=user_id, role="model", content=ai_text)
        db.add(new_user_msg)
        db.add(new_ai_msg)
        db.commit()

        return ai_text

    except Exception as e:
        print(f"AI Error: {e}")
        return "Sorry, I'm having trouble thinking right now."
    finally:
        db.close()