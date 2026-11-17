"""
Centralized Configuration for PulseOps AI
Loads environment variables and provides structured settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Root Directory of the project
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(ROOT_DIR / ".env")


class Config:
    # 1. Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # 2. Notion Configuration
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_PAGE_ID: str = os.getenv("NOTION_PAGE_ID", "")

    # 3. Jira Cloud Configuration
    JIRA_INSTANCE_URL: str = os.getenv("JIRA_INSTANCE_URL", "").rstrip("/")
    JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "KAN")
    JIRA_USER_EMAIL: str = os.getenv("JIRA_USER_EMAIL", "")
    JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")

    # 4. LLM API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # 5. LangSmith Observability
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "pulseops-ai")


config = Config()
