# AI Reminder Bot

This project is a sophisticated, AI-powered Discord bot designed to act as a personal assistant. It leverages natural language processing to manage reminders, schedules, and tasks, all within a Discord chat.

## 🌟 Features

- **Natural Language Understanding**: Powered by Google's Gemini Pro, the bot can understand conversational requests to set, list, and complete reminders.
- **Proactive Reminders**: The bot doesn't just set reminders; it actively "nags" you about overdue tasks until they are marked as complete.
- **Task Management**:
  - `!reminders`: Lists all your pending tasks.
  - `!done <task_id>`: Marks a specific task as completed.
- **AI-Powered Chat**: Engage in a natural conversation with the bot. It remembers your chat history to provide context-aware responses.
- **Schedule Checking**: The bot can retrieve your timetable for a specific day.

## 🛠️ Technology Stack

- **Backend**: Python
- **Discord API**: `discord.py`
- **AI/NLP**: Google Gemini (`google-genai`)
- **Database**: PostgreSQL with `SQLAlchemy` for ORM.
- **Containerization**: Docker & Docker Compose
- **CI/CD**: Automated builds and deployments using GitHub Actions.

## 🏗️ Architecture

The application is containerized using Docker and consists of two main services orchestrated by Docker Compose:

1.  **`bot`**: The Python application running the Discord bot.
2.  **`db`**: The PostgreSQL database for storing user data, reminders, and chat history.

The Python application itself is structured into three key modules:

- `app/main.py`: The main entry point for the bot, handling Discord events and command routing.
- `app/ai_logic.py`: Contains all the "brains" of the operation, interfacing with the Gemini AI and defining the function calls for the bot's tools.
- `app/database.py`: Manages the database schema (`Reminders`, `Timetable`, `ChatHistory`) and all database sessions.

## 🚀 Deployment

Deployment is fully automated via a CI/CD pipeline in GitHub Actions (`.github/workflows/deploy.yml`):

1.  **Push to `main`**: Any push to the `main` branch triggers the workflow.
2.  **Build and Push**: A Docker image is built and pushed to Docker Hub.
3.  **Deploy**: The workflow then connects to the production server via SSH, pulls the latest Docker image from Docker Hub, and restarts the `docker-compose` stack with the new image.

## ⚙️ Setup & Installation

To run this project locally, you will need to have Docker and Docker Compose installed.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/ai-reminder-bot.git
    cd ai-reminder-bot
    ```

2.  **Create a `.env` file**:
    Based on the `docker-compose.yml` and `.github/workflows/deploy.yml` files, you will need to create a `.env` file with the following variables:

    ```env
    DISCORD_TOKEN=your_discord_bot_token
    GEMINI_API_KEY=your_gemini_api_key
    ADMIN_ID=your_discord_user_id
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_NAME=your_db_name
    DATABASE_URL=postgresql+psycopg2://your_db_user:your_db_password@db:5432/your_db_name
    ```

3.  **Build and run with Docker Compose**:
    ```bash
    docker-compose up --build -d
    ```
