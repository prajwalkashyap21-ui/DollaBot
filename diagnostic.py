import os
import time
from dotenv import load_dotenv
import psycopg2
import google.generativeai as genai

load_dotenv()

print("--- DIAGNOSTIC TEST ---")

# 1. Test Database
start_db = time.time()
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    cursor.fetchone()
    cursor.close()
    conn.close()
    print(f"Database Connection: {time.time() - start_db:.2f} seconds")
except Exception as e:
    print(f"Database Error: {e}")

# 2. Test Gemini API
start_ai = time.time()
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-flash-lite-latest")
    response = model.generate_content("Say hello in one word.")
    print(f"Gemini API Response: {time.time() - start_ai:.2f} seconds")
    print(f"Gemini Output: {response.text.strip()}")
except Exception as e:
    print(f"Gemini Error: {e}")
