import sqlite3
from datetime import datetime
import os

# Создаем резервную копию старой базы, если она есть
if os.path.exists('star_bot.db'):
    import shutil
    backup_name = f'star_bot_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    shutil.copy('star_bot.db', backup_name)
    print(f"✅ Создана резервная копия: {backup_name}")

conn = sqlite3.connect('star_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Создает все таблицы с нуля, сохраняя данные через временные таблицы"""
    
    # Проверяем, есть ли уже данные в старой базе
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    old_data_exists = cursor.fetchone() is not None
    
    if old_data_exists:
        print("📦 Обнаружена старая база данных, переносим данные...")
        
        # Сохраняем старые данные во временные таблицы
        cursor.execute('CREATE TEMP TABLE temp_users AS SELECT * FROM users')
        cursor.execute('CREATE TEMP TABLE temp_channels AS SELECT * FROM channels')
        cursor.execute('CREATE TEMP TABLE temp_completions AS SELECT * FROM completions')
        cursor.execute('CREATE TEMP TABLE temp_withdrawal_requests AS SELECT * FROM withdrawal_requests')
        cursor.execute('CREATE TEMP TABLE temp_giveaways AS SELECT * FROM giveaways')
        cursor.execute('CREATE TEMP TABLE temp_giveaway_participants AS SELECT * FROM giveaway_participants')
        cursor.execute('CREATE TEMP TABLE temp_games AS SELECT * FROM games')
        conn.commit()
        
        # Удаляем старые таблицы
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('DROP TABLE IF EXISTS channels')
        cursor.execute('DROP TABLE IF EXISTS completions')
        cursor.execute('DROP TABLE IF EXISTS withdrawal_requests')
        cursor.execute('DROP TABLE IF EXISTS giveaways')
        cursor.execute('DROP TABLE IF EXISTS giveaway_participants')
        cursor.execute('DROP TABLE IF EXISTS games')
        cursor.execute('DROP TABLE IF EXISTS transactions')
        cursor.execute('DROP TABLE IF EXISTS referral_bonuses')
        cursor.execute('DROP TABLE IF EXISTS stats')
        conn.commit()
    
    # ========== СОЗДАНИЕ НОВЫХ ТАБЛИЦ ==========
    
    # 1. Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        balance REAL DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        ref_by INTEGER DEFAULT NULL,
        tasks_completed INTEGER DEFAULT 0,
        last_daily TIMESTAMP,
        last_hourly TIMESTAMP,
        total_earned REAL DEFAULT 0,
        total_withdrawn REAL DEFAULT 0,
        register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        language TEXT DEFAULT 'ru',
        warns INTEGER DEFAULT 0
    )''')
    
    # 2. Таблица каналов
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        name TEXT,
        stars REAL DEFAULT 0.25,
        is_required INTEGER DEFAULT 0,
        added_by INTEGER,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 3. Таблица выполненных заданий
    cursor.execute('''CREATE TABLE IF NOT EXISTS completions (
        user_id INTEGER,
        channel_id TEXT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        earned REAL,
        PRIMARY KEY (user_id, channel_id)
    )''')
    
    # 4. Таблица заявок на вывод
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending',
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        processed_by INTEGER,
        reject_reason TEXT
    )''')
    
    # 5. Таблица розыгрышей
    cursor.execute('''CREATE TABLE IF NOT EXISTS giveaways (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        prize TEXT,
        end_date TIMESTAMP,
        required_channels TEXT,
        is_active INTEGER DEFAULT 1,
        winner_id INTEGER,
        winner_username TEXT,
        message_id INTEGER,
        channel_post_id INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        participants_count INTEGER DEFAULT 0
    )''')
    
    # 6. Таблица участников розыгрышей
    cursor.execute('''CREATE TABLE IF NOT EXISTS giveaway_participants (
        giveaway_id INTEGER,
        user_id INTEGER,
        username TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_winner INTEGER DEFAULT 0,
        PRIMARY KEY (giveaway_id, user_id)
    )''')
    
    # 7. Таблица мини-игр
    cursor.execute('''CREATE TABLE IF NOT EXISTS games (
        user_id INTEGER PRIMARY KEY,
        games_played INTEGER DEFAULT 0,
        games_won INTEGER DEFAULT 0,
        total_spent REAL DEFAULT 0,
        total_won REAL DEFAULT 0,
        last_played TIMESTAMP
    )''')
    
    # 8. Таблица транзакций
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        type TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 9. Таблица реферальных бонусов
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_bonuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        bonus_amount REAL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid_at TIMESTAMP
    )''')
    
    # 10. Таблица статистики
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (
        stat_key TEXT PRIMARY KEY,
        stat_value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    # ========== ВОССТАНОВЛЕНИЕ СТАРЫХ ДАННЫХ ==========
    if old_data_exists:
        print("📥 Восстанавливаем старые данные...")
        
        try:
            # Восстанавливаем пользователей
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, balance, is_banned, referrals, ref_by, tasks_completed, last_daily, last_hourly)
                SELECT user_id, username, balance, is_banned, referrals, ref_by, tasks_completed, last_daily, last_hourly 
                FROM temp_users
            ''')
            
            # Восстанавливаем каналы
            cursor.execute('''
                INSERT OR IGNORE INTO channels (channel_id, name, stars, is_required)
                SELECT channel_id, name, stars, is_required 
                FROM temp_channels
            ''')
            
            # Восстанавливаем выполненные задания
            cursor.execute('''
                INSERT OR IGNORE INTO completions (user_id, channel_id, completed_at, earned)
                SELECT user_id, channel_id, completed_at, earned 
                FROM temp_completions
            ''')
            
            # Восстанавливаем заявки на вывод
            cursor.execute('''
                INSERT OR IGNORE INTO withdrawal_requests (id, user_id, username, amount, status, requested_at)
                SELECT id, user_id, username, amount, status, requested_at 
                FROM temp_withdrawal_requests
            ''')
            
            # Восстанавливаем розыгрыши
            cursor.execute('''
                INSERT OR IGNORE INTO giveaways (id, title, prize, end_date, required_channels, is_active, winner_id, winner_username, message_id, created_at)
                SELECT id, title, prize, end_date, required_channels, is_active, winner_id, winner_username, message_id, created_at 
                FROM temp_giveaways
            ''')
            
            # Восстанавливаем участников
            cursor.execute('''
                INSERT OR IGNORE INTO giveaway_participants (giveaway_id, user_id, username, joined_at)
                SELECT giveaway_id, user_id, username, joined_at 
                FROM temp_giveaway_participants
            ''')
            
            # Восстанавливаем игры
            cursor.execute('''
                INSERT OR IGNORE INTO games (user_id, games_played, games_won)
                SELECT user_id, games_played, games_won 
                FROM temp_games
            ''')
            
            conn.commit()
            print("✅ Старые данные успешно восстановлены!")
            
            # Удаляем временные таблицы
            cursor.execute('DROP TABLE temp_users')
            cursor.execute('DROP TABLE temp_channels')
            cursor.execute('DROP TABLE temp_completions')
            cursor.execute('DROP TABLE temp_withdrawal_requests')
            cursor.execute('DROP TABLE temp_giveaways')
            cursor.execute('DROP TABLE temp_giveaway_participants')
            cursor.execute('DROP TABLE temp_games')
            conn.commit()
            
        except Exception as e:
            print(f"⚠️ Ошибка при восстановлении данных: {e}")
            conn.rollback()
    
    # ========== ДОБАВЛЯЕМ ОБЯЗАТЕЛЬНЫЕ ДАННЫЕ ==========
    
    # Добавляем обязательный канал
    cursor.execute('SELECT * FROM channels WHERE channel_id = ?', ('UralchikStars',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO channels (channel_id, name, stars, is_required) 
            VALUES (?, ?, ?, ?)
        ''', ('UralchikStars', '📢 UralchikStars', 0, 1))
        print("✅ Добавлен обязательный канал")
    
    # Добавляем админа
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (7673683792,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, is_admin, balance) 
            VALUES (?, ?, ?, ?)
        ''', (7673683792, 'admin', 1, 0))
        print("✅ Добавлен администратор")
    else:
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = 7673683792')
        cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', ('admin', 7673683792))
        print("✅ Обновлен статус администратора")
    
    # Добавляем статистику
    cursor.execute('INSERT OR IGNORE INTO stats (stat_key, stat_value) VALUES (?, ?)', ('total_users', '0'))
    cursor.execute('INSERT OR IGNORE INTO stats (stat_key, stat_value) VALUES (?, ?)', ('total_earned', '0'))
    cursor.execute('INSERT OR IGNORE INTO stats (stat_key, stat_value) VALUES (?, ?)', ('total_withdrawn', '0'))
    
    conn.commit()
    print("✅ База данных готова к работе!")

# ========== ПОЛЬЗОВАТЕЛИ ==========
def add_user(user_id, username, first_name=None, last_name=None, ref_by=None):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, ref_by, register_date, last_activity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, ref_by, datetime.now(), datetime.now()))
        
        if ref_by:
            cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (ref_by,))
            cursor.execute('''
                INSERT INTO referral_bonuses (referrer_id, referred_id, bonus_amount) 
                VALUES (?, ?, ?)
            ''', (ref_by, user_id, 3))
        
        # Обновляем статистику
        cursor.execute('SELECT stat_value FROM stats WHERE stat_key = "total_users"')
        total = int(cursor.fetchone()[0]) + 1
        cursor.execute('UPDATE stats SET stat_value = ? WHERE stat_key = "total_users"', (str(total),))
        
        conn.commit()
        return True
    else:
        cursor.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', (datetime.now(), user_id))
        conn.commit()
        return False

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'balance': row[4],
            'is_banned': row[5],
            'is_admin': row[6],
            'referrals': row[7],
            'ref_by': row[8],
            'tasks_completed': row[9],
            'last_daily': row[10],
            'last_hourly': row[11],
            'total_earned': row[12],
            'total_withdrawn': row[13],
            'register_date': row[14],
            'last_activity': row[15],
            'language': row[16],
            'warns': row[17]
        }
    return None

def get_user_by_username(username):
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'balance': row[4],
            'is_banned': row[5],
            'is_admin': row[6],
            'referrals': row[7],
            'ref_by': row[8],
            'tasks_completed': row[9],
            'last_daily': row[10],
            'last_hourly': row[11],
            'total_earned': row[12],
            'total_withdrawn': row[13],
            'register_date': row[14],
            'last_activity': row[15],
            'language': row[16],
            'warns': row[17]
        }
    return None

def update_balance(user_id, delta, description=None):
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (delta, user_id))
    
    if delta > 0:
        cursor.execute('UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?', (delta, user_id))
        cursor.execute('UPDATE stats SET stat_value = stat_value + ? WHERE stat_key = "total_earned"', (delta,))
    elif delta < 0:
        cursor.execute('UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?', (abs(delta), user_id))
        cursor.execute('UPDATE stats SET stat_value = stat_value + ? WHERE stat_key = "total_withdrawn"', (abs(delta),))
    
    if description:
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, created_at) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, delta, 'earn' if delta > 0 else 'spend', description, datetime.now()))
    
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

def get_all_users():
    cursor.execute('SELECT user_id, username FROM users WHERE is_banned = 0')
    return cursor.fetchall()

def get_banned_users():
    cursor.execute('SELECT user_id, username FROM users WHERE is_banned = 1')
    return cursor.fetchall()

# ========== БОНУСЫ ==========
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

def set_daily_claimed(user_id):
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (datetime.now(), user_id))
    conn.commit()

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

def set_hourly_claimed(user_id):
    cursor.execute('UPDATE users SET last_hourly = ? WHERE user_id = ?', (datetime.now(), user_id))
    conn.commit()

# ========== КАНАЛЫ ==========
def add_channel(channel_id, name, stars=0.25, admin_id=None):
    cursor.execute('''
        INSERT OR IGNORE INTO channels (channel_id, name, stars, added_by, added_date) 
        VALUES (?, ?, ?, ?, ?)
    ''', (channel_id, name, stars, admin_id, datetime.now()))
    conn.commit()

def get_channels():
    cursor.execute('SELECT channel_id, name, stars FROM channels WHERE is_required = 0')
    return cursor.fetchall()

def get_all_channels():
    cursor.execute('SELECT * FROM channels')
    return cursor.fetchall()

def delete_channel(channel_id):
    cursor.execute('DELETE FROM channels WHERE channel_id = ? AND is_required = 0', (channel_id,))
    conn.commit()

def is_completed(user_id, channel_id):
    cursor.execute('SELECT 1 FROM completions WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
    return cursor.fetchone() is not None

def mark_completed(user_id, channel_id, earned=0.25):
    cursor.execute('''
        INSERT OR IGNORE INTO completions (user_id, channel_id, completed_at, earned) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, channel_id, datetime.now(), earned))
    cursor.execute('UPDATE users SET tasks_completed = tasks_completed + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def get_completed_count(user_id):
    cursor.execute('SELECT tasks_completed FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def reset_completions(user_id):
    cursor.execute('DELETE FROM completions WHERE user_id = ?', (user_id,))
    cursor.execute('UPDATE users SET tasks_completed = 0 WHERE user_id = ?', (user_id,))
    conn.commit()

# ========== ВЫВОД ==========
def add_withdrawal(user_id, username, amount):
    cursor.execute('''
        INSERT INTO withdrawal_requests (user_id, username, amount, requested_at) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, amount, datetime.now()))
    conn.commit()
    return cursor.lastrowid

def get_pending_withdrawals():
    cursor.execute('SELECT * FROM withdrawal_requests WHERE status = "pending" ORDER BY requested_at ASC')
    return cursor.fetchall()

def update_withdrawal_status(req_id, status, processed_by=None, reject_reason=None):
    cursor.execute('''
        UPDATE withdrawal_requests 
        SET status = ?, processed_at = ?, processed_by = ?, reject_reason = ?
        WHERE id = ?
    ''', (status, datetime.now(), processed_by, reject_reason, req_id))
    conn.commit()

# ========== РОЗЫГРЫШИ ==========
def add_giveaway(title, prize, end_date, required_channels, created_by=None):
    cursor.execute('''
        INSERT INTO giveaways (title, prize, end_date, required_channels, created_by, created_at, participants_count) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, prize, end_date, required_channels, created_by, datetime.now(), 0))
    conn.commit()
    return cursor.lastrowid

def get_active_giveaways():
    cursor.execute('''
        SELECT * FROM giveaways 
        WHERE is_active = 1 AND end_date > ? 
        ORDER BY end_date ASC
    ''', (datetime.now(),))
    return cursor.fetchall()

def get_all_giveaways(include_inactive=False):
    if include_inactive:
        cursor.execute('SELECT * FROM giveaways ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM giveaways WHERE is_active = 1 AND end_date > ? ORDER BY end_date ASC', (datetime.now(),))
    return cursor.fetchall()

def get_giveaway(giveaway_id):
    cursor.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,))
    return cursor.fetchone()

def update_giveaway(giveaway_id, **kwargs):
    allowed_fields = ['title', 'prize', 'end_date', 'required_channels', 'is_active']
    for key, value in kwargs.items():
        if key in allowed_fields:
            cursor.execute(f'UPDATE giveaways SET {key} = ? WHERE id = ?', (value, giveaway_id))
    conn.commit()
    return True

def delete_giveaway(giveaway_id):
    cursor.execute('DELETE FROM giveaway_participants WHERE giveaway_id = ?', (giveaway_id,))
    cursor.execute('DELETE FROM giveaways WHERE id = ?', (giveaway_id,))
    conn.commit()
    return True

def end_giveaway(giveaway_id, winner_id, winner_username):
    cursor.execute('''
        UPDATE giveaways 
        SET is_active = 0, winner_id = ?, winner_username = ? 
        WHERE id = ?
    ''', (winner_id, winner_username, giveaway_id))
    conn.commit()

def add_participant(giveaway_id, user_id, username):
    cursor.execute('''
        INSERT OR IGNORE INTO giveaway_participants (giveaway_id, user_id, username, joined_at) 
        VALUES (?, ?, ?, ?)
    ''', (giveaway_id, user_id, username, datetime.now()))
    if cursor.rowcount:
        cursor.execute('UPDATE giveaways SET participants_count = participants_count + 1 WHERE id = ?', (giveaway_id,))
    conn.commit()

def get_participants(giveaway_id):
    cursor.execute('SELECT user_id, username FROM giveaway_participants WHERE giveaway_id = ?', (giveaway_id,))
    return cursor.fetchall()

def is_participant(giveaway_id, user_id):
    cursor.execute('SELECT 1 FROM giveaway_participants WHERE giveaway_id = ? AND user_id = ?', (giveaway_id, user_id))
    return cursor.fetchone() is not None

def set_giveaway_message_id(giveaway_id, message_id):
    cursor.execute('UPDATE giveaways SET message_id = ? WHERE id = ?', (message_id, giveaway_id))
    conn.commit()

def get_giveaway_participants_count(giveaway_id):
    cursor.execute('SELECT COUNT(*) FROM giveaway_participants WHERE giveaway_id = ?', (giveaway_id,))
    return cursor.fetchone()[0]

# ========== МИНИ-ИГРЫ ==========
def add_game_result(user_id, won, spent=5, won_amount=25):
    cursor.execute('SELECT * FROM games WHERE user_id = ?', (user_id,))
    game = cursor.fetchone()
    
    if game:
        cursor.execute('''
            UPDATE games SET 
                games_played = games_played + 1,
                games_won = games_won + ?,
                total_spent = total_spent + ?,
                total_won = total_won + ?,
                last_played = ?
            WHERE user_id = ?
        ''', (1 if won else 0, spent, won_amount if won else 0, datetime.now(), user_id))
    else:
        cursor.execute('''
            INSERT INTO games (user_id, games_played, games_won, total_spent, total_won, last_played) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 1, 1 if won else 0, spent, won_amount if won else 0, datetime.now()))
    
    conn.commit()

def get_game_stats(user_id):
    cursor.execute('SELECT games_played, games_won FROM games WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

# ========== ТРАНЗАКЦИИ ==========
def get_user_transactions(user_id, limit=10):
    cursor.execute('''
        SELECT amount, type, description, created_at 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    return cursor.fetchall()

print("✅ Модуль database.py загружен")
