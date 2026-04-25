import sqlite3
from datetime import datetime
import os

DB_FILE = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            payment_source TEXT,
            description TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_expense(user_id, amount, category, payment_source, description, date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (user_id, amount, category, payment_source, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, category, payment_source, description, date))
    conn.commit()
    conn.close()

def get_monthly_total(user_id):
    current_month = datetime.now().strftime("%Y-%m")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND date LIKE ?
    ''', (user_id, f"{current_month}%"))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0

def get_recent_expenses(user_id, limit=5):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, category, payment_source, description, date FROM expenses 
        WHERE user_id = ? ORDER BY date DESC LIMIT ?
    ''', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results
