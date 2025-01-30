# app/core/openai_client.py
from openai import AsyncOpenAI
import os
import logging

try:
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    client = None