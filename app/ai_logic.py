import os
from google import genai
from google.genai import types
from app.database import SessionLocal, Reminder, Timetable, ChatHistory
from datetime import datetime, timedelta
import pytz

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- ADVANCED TOOLS ---

def add_reminder(user_id: str, task: str, time_str: str):
    """Adds a reminder. time_str format: 'YYYY-MM-DD HH:MM'"""
    db = SessionLocal()
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        new_task = Reminder(user_id=user_id, task=task, remind_at=dt)
        db.add(new_task)
        db.commit()
        return f"✅ Done! I've noted down: '{task}' for {time_str}."
    finally:
        db.close()

def get_reminders(user_id: str):
    """Lists all pending tasks and unfinished work."""
    db = SessionLocal()
    try:
        tasks = db.query(Reminder).filter(Reminder.user_id == user_id).all()
        if not tasks:
            return "You don't have any unfinished work right now! You're all caught up."
        
        res = "Here is your unfinished work:\n"
        for t in tasks:
            res += f"• [ID: {t.id}] {t.task} (Due: {t.remind_at.strftime('%H:%M, %d %b')})\n"
        return res
    finally:
        db.close()

def complete_task(user_id: str, task_id: int):
    """Marks a specific task as finished/done."""
    db = SessionLocal()
    try:
        task = db.query(Reminder).filter(Reminder.id == task_id, Reminder.user_id == user_id).first()
        if task:
            task_name = task.task
            db.delete(task)
            db.commit()
            return f"Great job! I've marked '{task_name}' as completed."
        return f"I couldn't find a task with ID {task_id}."
    finally:
        db.close()

def clear_all_reminders(user_id: str):
    """Deletes ALL reminders/tasks for the user. Use this when user says 'remove all tasks'."""
    db = SessionLocal()
    try:
        db.query(Reminder).filter(Reminder.user_id == user_id).delete()
        db.commit()
        return "Clean slate! I have removed all your pending tasks."
    finally:
        db.close()

def get_timetable_for_day(user_id: str, day: str):
    """Checks the campus schedule for a specific day (e.g., 'Monday')."""
    db = SessionLocal()
    try:
        entries = db.query(Timetable).filter(Timetable.user_id == user_id, Timetable.day.ilike(day)).all()
        if not entries:
            return f"You have nothing scheduled for {day}."
        res = f"Your {day} schedule:\n"
        for e in entries:
            res += f"• {e.time}: {e.subject}\n"
        return res
    finally:
        db.close()

# --- THE AI BRAIN ---

def get_ai_response(user_input: str, user_id: str):
    db = SessionLocal()
    tz = pytz.timezone('Asia/Colombo')
    now_dt = datetime.now(tz)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M, %A")
    
    # Context Fetching
    history_records = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.timestamp.desc()).limit(12).all()
    history_records.reverse()

    contents = [types.Content(role=r.role, parts=[types.Part(text=r.content)]) for r in history_records]
    contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

    # ADVANCED SYSTEM INSTRUCTIONS
    sys_msg = (
        f"Today is {now_str}. You are a highly intelligent, proactive, and human-like personal assistant. "
        f"Your goal is to help user {user_id} manage their life seamlessly.\n\n"
        "GUIDELINES:\n"
        "1. BE PROACTIVE: If a user says 'I'm tired', offer to clear their tasks or remind them to rest.\n"
        "2. UNDERSTAND INTENT: If they ask for 'unfinished work', call 'get_reminders'. If they say 'delete everything', call 'clear_all_reminders'.\n"
        "3. NATURAL LANGUAGE: Don't sound like a bot. Use phrases like 'I've got you covered' or 'All set!'.\n"
        "4. TIME SENSITIVITY: If someone says 'next Monday', calculate the date based on today's date.\n"
        "5. ALWAYS use tools. Never tell the user you 'can't' do something if a tool exists for it."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=sys_msg,
                tools=[add_reminder, get_reminders, complete_task, clear_all_reminders, get_timetable_for_day],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
            )
        )
        
        ai_text = response.text if response.text else "Consider it done!"

        # Persistence
        db.add(ChatHistory(user_id=user_id, role="user", content=user_input))
        db.add(ChatHistory(user_id=user_id, role="model", content=ai_text))
        db.commit()
        return ai_text

    except Exception as e:
        print(f"Brain Error: {e}")
        return "I'm having a bit of a 'brain fog' moment. Can you say that again?"
    finally:
        db.close()