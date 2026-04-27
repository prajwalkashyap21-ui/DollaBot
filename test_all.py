import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

models_to_test = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-flash-latest"
]

print("--- SPEED TEST ---")
for m in models_to_test:
    start_ai = time.time()
    try:
        response = client.models.generate_content(
            model=m,
            contents="Hello"
        )
        print(f"[{m}] Success: {time.time() - start_ai:.2f}s")
    except Exception as e:
        print(f"[{m}] Failed: {e}")
