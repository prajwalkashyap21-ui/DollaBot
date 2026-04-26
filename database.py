import psycopg2
from psycopg2 import pool
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_POOL = None

def init_db():
    global DB_POOL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables. Please check your .env file.")
    
    # Create a connection pool to eliminate the massive 1-2 second connection delay per query
    DB_POOL = psycopg2.pool.ThreadedConnectionPool(1, 10, db_url)
    
    conn = DB_POOL.getconn()
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount REAL,
            person_name TEXT,
            debt_type TEXT,
            is_cleared BOOLEAN DEFAULT FALSE,
            date TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount REAL,
            category TEXT,
            payee TEXT,
            description TEXT,
            is_autopay BOOLEAN,
            day_of_month INTEGER,
            last_paid_month TEXT,
            last_notified_month TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

# --- EXPENSE FUNCTIONS ---
def add_expense(user_id, amount, category, payment_source, description, date=None):
    if date is None:
        date = datetime.now()
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (user_id, amount, category, payment_source, description, date)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (user_id, amount, category, payment_source, description, date))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def get_monthly_total(user_id):
    current_month_str = datetime.now().strftime("%Y-%m")
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s
    ''', (user_id, current_month_str))
    result = cursor.fetchone()[0]
    cursor.close()
    DB_POOL.putconn(conn)
    return result if result else 0.0

def get_recent_expenses(user_id, limit=5):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, category, payment_source, description, TO_CHAR(date, 'YYYY-MM-DD HH24:MI:SS') FROM expenses 
        WHERE user_id = %s ORDER BY date DESC LIMIT %s
    ''', (user_id, limit))
    results = cursor.fetchall()
    cursor.close()
    DB_POOL.putconn(conn)
    return results

# --- DEBT FUNCTIONS ---
def add_debt(user_id, amount, person_name, debt_type):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO debts (user_id, amount, person_name, debt_type, date)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, amount, person_name, debt_type, datetime.now()))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def clear_debt(user_id, person_name):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE debts SET is_cleared = TRUE 
        WHERE user_id = %s AND LOWER(person_name) = LOWER(%s)
    ''', (user_id, person_name))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def get_uncleared_debts(user_id):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, person_name, debt_type FROM debts 
        WHERE user_id = %s AND is_cleared = FALSE
    ''', (user_id,))
    results = cursor.fetchall()
    cursor.close()
    DB_POOL.putconn(conn)
    return results

# --- RECURRING / SUBSCRIPTION FUNCTIONS ---
def add_recurring(user_id, amount, category, payee, description, is_autopay, day_of_month):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recurring (user_id, amount, category, payee, description, is_autopay, day_of_month)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (user_id, amount, category, payee, description, is_autopay, day_of_month))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def update_recurring_amount(user_id, payee, new_amount):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE recurring SET amount = %s WHERE user_id = %s AND LOWER(payee) = LOWER(%s)
    ''', (new_amount, user_id, payee))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def update_recurring_date(user_id, payee, new_day):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE recurring SET day_of_month = %s WHERE user_id = %s AND LOWER(payee) = LOWER(%s)
    ''', (new_day, user_id, payee))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def mark_recurring_paid(user_id, payee, current_month_str):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE recurring SET last_paid_month = %s WHERE user_id = %s AND LOWER(payee) = LOWER(%s)
    ''', (current_month_str, user_id, payee))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def mark_recurring_notified(recurring_id, current_month_str):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE recurring SET last_notified_month = %s WHERE id = %s
    ''', (current_month_str, recurring_id))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)

def get_all_recurring(user_id):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, amount, category, payee, description, is_autopay, day_of_month, last_paid_month, last_notified_month 
        FROM recurring WHERE user_id = %s
    ''', (user_id,))
    results = cursor.fetchall()
    cursor.close()
    DB_POOL.putconn(conn)
    return results

# --- SETTINGS / USERS ---
def get_all_users():
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT user_id FROM expenses
        UNION SELECT DISTINCT user_id FROM debts
        UNION SELECT DISTINCT user_id FROM recurring
    ''')
    results = [row[0] for row in cursor.fetchall()]
    cursor.close()
    DB_POOL.putconn(conn)
    return results

def get_setting(key):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = %s', (key,))
    result = cursor.fetchone()
    cursor.close()
    DB_POOL.putconn(conn)
    return result[0] if result else None

def set_setting(key, value):
    conn = DB_POOL.getconn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    ''', (key, value))
    conn.commit()
    cursor.close()
    DB_POOL.putconn(conn)
