import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define the tools the AI can use
def create_reminder(task: str, time_str: str):
    """Saves a reminder to the database."""
    # Logic to parse time and save to DB
    return f"Reminder for {task} set for {time_str}"

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[create_reminder] # Tell Gemini it can call this function
)