import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables. Please check your .env file.")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount REAL,
            category TEXT,
            payment_source TEXT,
            description TEXT,
            date TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def add_expense(user_id, amount, category, payment_source, description, date=None):
    if date is None:
        date = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (user_id, amount, category, payment_source, description, date)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (user_id, amount, category, payment_source, description, date))
    conn.commit()
    cursor.close()
    conn.close()

def get_monthly_total(user_id):
    current_month_str = datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s
    ''', (user_id, current_month_str))
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return result if result else 0.0

def get_recent_expenses(user_id, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, category, payment_source, description, TO_CHAR(date, 'YYYY-MM-DD HH24:MI:SS') FROM expenses 
        WHERE user_id = %s ORDER BY date DESC LIMIT %s
    ''', (user_id, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
