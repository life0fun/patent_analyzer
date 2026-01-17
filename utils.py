import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback for checking if user provided it in another way or just let it fail naturally
        pass 
    return OpenAI(api_key=api_key)
