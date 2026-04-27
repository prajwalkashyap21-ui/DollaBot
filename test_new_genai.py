import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

print("--- NEW GENAI SDK TEST ---")
start_ai = time.time()
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents="Say hello in one word."
    )
    print(f"Gemini API Response: {time.time() - start_ai:.2f} seconds")
    print(f"Gemini Output: {response.text.strip()}")
except Exception as e:
    print(f"Gemini Error: {e}")
