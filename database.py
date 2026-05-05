import sqlite3

conn = sqlite3.connect('star_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            ref_by INTEGER DEFAULT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            name TEXT,
            stars REAL DEFAULT 0.25
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completions (
            user_id INTEGER,
            channel_id TEXT,
            PRIMARY KEY (user_id, channel_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawal_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()

def add_user(user_id, ref_by=None):
    cursor.execute('INSERT OR IGNORE INTO users (user_id, ref_by) VALUES (?, ?)', (user_id, ref_by))
    if ref_by and cursor.rowcount:
        cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (ref_by,))
        cursor.execute('UPDATE users SET balance = balance + 3 WHERE user_id = ?', (ref_by,))
    conn.commit()

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def update_balance(user_id, delta):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (delta, user_id))
    conn.commit()

def add_channel(channel_id, name):
    cursor.execute('INSERT OR IGNORE INTO channels (channel_id, name) VALUES (?, ?)', (channel_id, name))
    conn.commit()

def get_channels():
    cursor.execute('SELECT * FROM channels')
    return cursor.fetchall()

def delete_channel(channel_id):
    cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
    conn.commit()

def is_completed(user_id, channel_id):
    cursor.execute('SELECT 1 FROM completions WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
    return cursor.fetchone() is not None

def mark_completed(user_id, channel_id):
    cursor.execute('INSERT INTO completions (user_id, channel_id) VALUES (?, ?)', (user_id, channel_id))
    conn.commit()

def add_withdrawal(user_id, amount):
    cursor.execute('INSERT INTO withdrawal_requests (user_id, amount) VALUES (?, ?)', (user_id, amount))
    conn.commit()

def get_pending_withdrawals():
    cursor.execute('SELECT * FROM withdrawal_requests WHERE status = "pending"')
    return cursor.fetchall()

def update_withdrawal_status(req_id, status):
    cursor.execute('UPDATE withdrawal_requests SET status = ? WHERE id = ?', (status, req_id))
    conn.commit()

def get_all_users():
    cursor.execute('SELECT user_id FROM users')
    return [row[0] for row in cursor.fetchall()]

def ban_user(user_id):
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def unban_user(user_id):
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()

def set_balance(user_id, new_balance):
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
