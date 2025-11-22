import sqlite3

DATABASE_NAME = 'premium_bot.db'

def setup_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_premium BOOLEAN DEFAULT 0
        )
    ''')
    
    # Payments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount TEXT,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'Pending' -- Pending, Confirmed, Rejected
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def add_new_payment(user_id, amount, screenshot_file_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, screenshot_file_id) VALUES (?, ?, ?)", 
                   (user_id, amount, screenshot_file_id))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id

def update_payment_status(payment_id, status, user_id=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status = ? WHERE payment_id = ?", 
                   (status, payment_id))
    
    # Agar status 'Confirmed' hai, toh user ko premium bana do
    if status == 'Confirmed' and user_id:
        cursor.execute("INSERT OR REPLACE INTO users (user_id, is_premium) VALUES (?, ?)", 
                       (user_id, 1))

    conn.commit()
    conn.close()
