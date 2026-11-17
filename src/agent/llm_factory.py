"""
PulseOps AI - LLM Provider Factory
Initializes OpenAI or Gemini models based on .env configuration,
with an intelligent deterministic fallback if no keys are currently set.
"""

import os
from typing import Optional
from src.config import config


def get_chat_model(temperature: float = 0.2):
    """
    Returns an initialized LangChain chat model.
    Prioritizes OpenAI -> Gemini -> Fallback.
    """
    openai_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
    gemini_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    # 1. OpenAI
    if openai_key and not openai_key.startswith("sk-proj-xxx"):
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=temperature,
                api_key=openai_key
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ChatOpenAI: {e}")

    # 2. Google Gemini
    if gemini_key and not gemini_key.startswith("AIzaxxx"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                temperature=temperature,
                google_api_key=gemini_key
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ChatGoogleGenerativeAI: {e}")

    return None
