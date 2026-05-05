import sqlite3
from datetime import datetime

conn = sqlite3.connect('star_bot.db', check_same_thread=False)
cursor = conn.cursor()

def migrate_db():
    """Обновляет базу данных без потери данных"""
    
    # 1. Проверяем и добавляем новые столбцы в users
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'username' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN username TEXT')
    if 'last_daily' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN last_daily TIMESTAMP')
    if 'last_hourly' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN last_hourly TIMESTAMP')
    
    # 2. Добавляем столбец is_required в channels
    cursor.execute("PRAGMA table_info(channels)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_required' not in columns:
        cursor.execute('ALTER TABLE channels ADD COLUMN is_required INTEGER DEFAULT 0')
    
    # 3. Добавляем обязательный канал (если его нет)
    cursor.execute('SELECT * FROM channels WHERE channel_id = ?', ('UralchikStars',))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO channels (channel_id, name, stars, is_required) VALUES (?, ?, ?, ?)',
                       ('UralchikStars', '📢 UralchikStars', 0, 1))
    
    conn.commit()

def init_db():
    """Создаёт только новые таблицы, не трогая существующие"""
    
    # Таблица пользователей (только если нет)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        ref_by INTEGER DEFAULT NULL,
        tasks_completed INTEGER DEFAULT 0,
        last_daily TIMESTAMP,
        last_hourly TIMESTAMP
    )''')
    
    # Таблица каналов
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        name TEXT,
        stars REAL DEFAULT 0.25,
        is_required INTEGER DEFAULT 0
    )''')
    
    # Таблица выполненных заданий
    cursor.execute('''CREATE TABLE IF NOT EXISTS completions (
        user_id INTEGER,
        channel_id TEXT,
        PRIMARY KEY (user_id, channel_id)
    )''')
    
    # Таблица заявок на вывод
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending'
    )''')
    
    # Таблица розыгрышей
    cursor.execute('''CREATE TABLE IF NOT EXISTS giveaways (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        prize TEXT,
        end_date TIMESTAMP,
        required_channels TEXT,
        is_active INTEGER DEFAULT 1,
        winner_id INTEGER,
        message_id INTEGER,
        channel_post_id INTEGER
    )''')
    
    # Таблица участников розыгрышей
    cursor.execute('''CREATE TABLE IF NOT EXISTS giveaway_participants (
        giveaway_id INTEGER,
        user_id INTEGER,
        joined_at TIMESTAMP,
        PRIMARY KEY (giveaway_id, user_id)
    )''')
    
    # Таблица мини-игр
    cursor.execute('''CREATE TABLE IF NOT EXISTS games (
        user_id INTEGER PRIMARY KEY,
        games_played INTEGER DEFAULT 0,
        games_won INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    
    # Запускаем миграцию (добавляем новые столбцы в существующие таблицы)
    migrate_db()

# ========== ПОЛЬЗОВАТЕЛИ ==========
def add_user(user_id, username, ref_by=None):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id, username, ref_by) VALUES (?, ?, ?)', 
                      (user_id, username, ref_by))
        if ref_by:
            cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (ref_by,))
        conn.commit()
    else:
        # Обновляем username (на случай если изменился)
        cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
        conn.commit()

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def update_balance(user_id, delta):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (delta, user_id))
    conn.commit()

def set_balance(user_id, new_balance):
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()

def ban_user(user_id):
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def unban_user(user_id):
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()

def get_user_by_username(username):
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

def update_username(user_id, username):
    cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
    conn.commit()

def get_all_users():
    cursor.execute('SELECT user_id, username FROM users WHERE is_banned = 0')
    return cursor.fetchall()

def get_banned_users():
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 1')
    return [row[0] for row in cursor.fetchall()]

# ========== БОНУСЫ ==========
def set_daily_claimed(user_id):
    cursor.execute('UPDATE users SET last_daily = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
    conn.commit()

def set_hourly_claimed(user_id):
    cursor.execute('UPDATE users SET last_hourly = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
    conn.commit()

def can_claim_daily(user_id):
    cursor.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return True
    try:
        last = datetime.fromisoformat(row[0])
        return (datetime.now() - last).total_seconds() >= 86400
    except:
        return True

def can_claim_hourly(user_id):
    cursor.execute('SELECT last_hourly FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return True
    try:
        last = datetime.fromisoformat(row[0])
        return (datetime.now() - last).total_seconds() >= 3600
    except:
        return True

# ========== КАНАЛЫ ==========
def add_channel(channel_id, name, stars=0.25):
    cursor.execute('INSERT OR IGNORE INTO channels (channel_id, name, stars, is_required) VALUES (?, ?, ?, 0)', 
                  (channel_id, name, stars))
    conn.commit()

def get_channels():
    """Получает только обычные каналы (не обязательные)"""
    cursor.execute('SELECT * FROM channels WHERE is_required = 0')
    return cursor.fetchall()

def get_all_channels():
    """Получает все каналы (включая обязательный)"""
    cursor.execute('SELECT * FROM channels')
    return cursor.fetchall()

def get_required_channel():
    """Получает обязательный канал"""
    cursor.execute('SELECT * FROM channels WHERE is_required = 1')
    return cursor.fetchone()

def delete_channel(channel_id):
    cursor.execute('DELETE FROM channels WHERE channel_id = ? AND is_required = 0', (channel_id,))
    conn.commit()

def is_completed(user_id, channel_id):
    cursor.execute('SELECT 1 FROM completions WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
    return cursor.fetchone() is not None

def mark_completed(user_id, channel_id):
    cursor.execute('INSERT OR IGNORE INTO completions (user_id, channel_id) VALUES (?, ?)', (user_id, channel_id))
    # Обновляем счетчик выполненных заданий
    cursor.execute('UPDATE users SET tasks_completed = tasks_completed + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def get_completed_count(user_id):
    cursor.execute('SELECT tasks_completed FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def reset_completions(user_id):
    """Сбрасывает выполненные задания (для проверки подписки)"""
    cursor.execute('DELETE FROM completions WHERE user_id = ?', (user_id,))
    cursor.execute('UPDATE users SET tasks_completed = 0 WHERE user_id = ?', (user_id,))
    conn.commit()

# ========== ВЫВОД ==========
def add_withdrawal(user_id, username, amount):
    cursor.execute('INSERT INTO withdrawal_requests (user_id, username, amount) VALUES (?, ?, ?)', 
                  (user_id, username, amount))
    conn.commit()

def get_pending_withdrawals():
    cursor.execute('SELECT * FROM withdrawal_requests WHERE status = "pending"')
    return cursor.fetchall()

def update_withdrawal_status(req_id, status):
    cursor.execute('UPDATE withdrawal_requests SET status = ? WHERE id = ?', (status, req_id))
    conn.commit()

# ========== РОЗЫГРЫШИ ==========
def add_giveaway(title, prize, end_date, required_channels, message_id=None):
    cursor.execute('''INSERT INTO giveaways (title, prize, end_date, required_channels, message_id, is_active) 
                      VALUES (?, ?, ?, ?, ?, 1)''', (title, prize, end_date, required_channels, message_id))
    conn.commit()
    return cursor.lastrowid

def get_active_giveaways():
    cursor.execute('SELECT * FROM giveaways WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP')
    return cursor.fetchall()

def get_giveaway(giveaway_id):
    cursor.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,))
    return cursor.fetchone()

def end_giveaway(giveaway_id, winner_id):
    cursor.execute('UPDATE giveaways SET is_active = 0, winner_id = ? WHERE id = ?', (winner_id, giveaway_id))
    conn.commit()

def add_participant(giveaway_id, user_id):
    cursor.execute('INSERT OR IGNORE INTO giveaway_participants (giveaway_id, user_id, joined_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                  (giveaway_id, user_id))
    conn.commit()

def get_participants(giveaway_id):
    cursor.execute('SELECT user_id FROM giveaway_participants WHERE giveaway_id = ?', (giveaway_id,))
    return [row[0] for row in cursor.fetchall()]

def is_participant(giveaway_id, user_id):
    cursor.execute('SELECT 1 FROM giveaway_participants WHERE giveaway_id = ? AND user_id = ?', (giveaway_id, user_id))
    return cursor.fetchone() is not None

def set_giveaway_message_id(giveaway_id, message_id):
    cursor.execute('UPDATE giveaways SET message_id = ? WHERE id = ?', (message_id, giveaway_id))
    conn.commit()

# ========== МИНИ-ИГРЫ ==========
def add_game_result(user_id, won):
    cursor.execute('INSERT INTO games (user_id, games_played, games_won) VALUES (?, 1, ?) ON CONFLICT(user_id) DO UPDATE SET '
                  'games_played = games_played + 1, games_won = games_won + ?', (user_id, 1 if won else 0, 1 if won else 0))
    conn.commit()

def get_game_stats(user_id):
    cursor.execute('SELECT games_played, games_won FROM games WHERE user_id = ?', (user_id,))
    return cursor.fetchone()
