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
        tables = ['users', 'channels', 'completions', 'withdrawal_requests', 'giveaways', 'giveaway_participants', 'games']
        for table in tables:
            try:
                cursor.execute(f'CREATE TEMP TABLE temp_{table} AS SELECT * FROM {table}')
            except:
                pass
        conn.commit()
        
        # Удаляем старые таблицы
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
            except:
                pass
        
        # Удаляем новые таблицы если есть
        cursor.execute('DROP TABLE IF EXISTS transactions')
        cursor.execute('DROP TABLE IF EXISTS referral_bonuses')
        cursor.execute('DROP TABLE IF EXISTS stats')
        cursor.execute('DROP TABLE IF EXISTS admins')
        cursor.execute('DROP TABLE IF EXISTS promocodes')
        cursor.execute('DROP TABLE IF EXISTS promocode_uses')
        cursor.execute('DROP TABLE IF EXISTS donations')
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
    
    # 11. Таблица администраторов
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 12. Таблица промокодов
    cursor.execute('''CREATE TABLE IF NOT EXISTS promocodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        reward REAL,
        uses_left INTEGER,
        max_uses INTEGER,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )''')
    
    # 13. Таблица использованных промокодов
    cursor.execute('''CREATE TABLE IF NOT EXISTS promocode_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        user_id INTEGER,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 14. Таблица донатов
    cursor.execute('''CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending',
        payment_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid_at TIMESTAMP
    )''')
    
    conn.commit()
    
    # ========== ВОССТАНОВЛЕНИЕ СТАРЫХ ДАННЫХ ==========
    if old_data_exists:
        print("📥 Восстанавливаем старые данные...")
        
        try:
            tables_to_restore = ['users', 'channels', 'completions', 'withdrawal_requests', 'giveaways', 'giveaway_participants', 'games']
            for table in tables_to_restore:
                try:
                    cursor.execute(f'INSERT OR IGNORE INTO {table} SELECT * FROM temp_{table}')
                    print(f"✅ Восстановлена таблица {table}")
                except Exception as e:
                    print(f"⚠️ Ошибка восстановления {table}: {e}")
            
            conn.commit()
            
            # Удаляем временные таблицы
            for table in tables_to_restore:
                try:
                    cursor.execute(f'DROP TABLE temp_{table}')
                except:
                    pass
            
            print("✅ Старые данные успешно восстановлены!")
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
    
    # Добавляем главного администратора
    cursor.execute('SELECT * FROM admins WHERE user_id = ?', (8508338715,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO admins (user_id, added_by) VALUES (?, ?)', (8508338715, 8508338715))
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (8508338715,))
        print("✅ Добавлен главный администратор")
    
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
        if username:
            cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
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

# ========== УПРАВЛЕНИЕ АДМИНАМИ ==========
def add_admin(user_id, added_by):
    """Добавляет администратора"""
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)', 
                   (user_id, added_by, datetime.now()))
    cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    return cursor.rowcount > 0

def remove_admin(user_id):
    """Удаляет администратора"""
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    cursor.execute('UPDATE users SET is_admin = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    return cursor.rowcount > 0

def get_all_admins():
    """Получает всех администраторов"""
    cursor.execute('''
        SELECT a.user_id, u.username, a.added_by, a.added_at 
        FROM admins a
        LEFT JOIN users u ON a.user_id = u.user_id
    ''')
    return cursor.fetchall()

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

# ========== ПРОМОКОДЫ ==========
def create_promocode(code, reward, max_uses, expires_at=None, created_by=None):
    """Создает новый промокод"""
    cursor.execute('''
        INSERT INTO promocodes (code, reward, uses_left, max_uses, created_by, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (code.upper(), reward, max_uses, max_uses, created_by, expires_at, datetime.now()))
    conn.commit()
    return cursor.lastrowid

def get_promocode(code):
    """Получает информацию о промокоде"""
    cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code.upper(),))
    return cursor.fetchone()

def use_promocode(code, user_id):
    """Использует промокод"""
    cursor.execute('SELECT * FROM promocodes WHERE code = ? AND is_active = 1 AND uses_left > 0', (code.upper(),))
    promo = cursor.fetchone()
    
    if not promo:
        return False, "Промокод не найден или неактивен"
    
    # Проверяем срок действия
    if promo[8] and datetime.fromisoformat(promo[8]) < datetime.now():
        cursor.execute('UPDATE promocodes SET is_active = 0 WHERE code = ?', (code.upper(),))
        conn.commit()
        return False, "Срок действия промокода истек"
    
    # Проверяем, использовал ли пользователь
    cursor.execute('SELECT 1 FROM promocode_uses WHERE code = ? AND user_id = ?', (code.upper(), user_id))
    if cursor.fetchone():
        return False, "Вы уже использовали этот промокод"
    
    # Начисляем награду
    reward = promo[2]
    update_balance(user_id, reward, f"Промокод: {code}")
    
    # Обновляем счетчик
    uses_left = promo[4] - 1
    cursor.execute('UPDATE promocodes SET uses_left = ? WHERE code = ?', (uses_left, code.upper()))
    cursor.execute('INSERT INTO promocode_uses (code, user_id, used_at) VALUES (?, ?, ?)', 
                   (code.upper(), user_id, datetime.now()))
    
    if uses_left == 0:
        cursor.execute('UPDATE promocodes SET is_active = 0 WHERE code = ?', (code.upper(),))
    
    conn.commit()
    return True, f"Вы получили {reward}⭐"

def get_all_promocodes():
    """Получает все промокоды"""
    cursor.execute('SELECT * FROM promocodes ORDER BY created_at DESC')
    return cursor.fetchall()

def delete_promocode(code):
    """Удаляет промокод"""
    cursor.execute('DELETE FROM promocodes WHERE code = ?', (code.upper(),))
    cursor.execute('DELETE FROM promocode_uses WHERE code = ?', (code.upper(),))
    conn.commit()
    return cursor.rowcount > 0

def get_promocode_stats(code):
    """Получает статистику использования промокода"""
    cursor.execute('SELECT COUNT(*) FROM promocode_uses WHERE code = ?', (code.upper(),))
    used_count = cursor.fetchone()[0]
    return used_count

# ========== ДОНАТЫ ==========
def create_donation(user_id, username, amount):
    """Создает запрос на донат"""
    cursor.execute('''
        INSERT INTO donations (user_id, username, amount, created_at, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, amount, datetime.now(), 'pending'))
    conn.commit()
    return cursor.lastrowid

def get_pending_donations():
    """Получает ожидающие донаты"""
    cursor.execute('SELECT * FROM donations WHERE status = "pending" ORDER BY created_at DESC')
    return cursor.fetchall()

def get_all_donations():
    """Получает все донаты"""
    cursor.execute('SELECT * FROM donations ORDER BY created_at DESC')
    return cursor.fetchall()

def get_user_donations(user_id):
    """Получает донаты пользователя"""
    cursor.execute('SELECT * FROM donations WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return cursor.fetchall()

def update_donation_status(donation_id, status, paid_at=None):
    """Обновляет статус доната"""
    cursor.execute('UPDATE donations SET status = ?, paid_at = ? WHERE id = ?', 
                   (status, paid_at or datetime.now(), donation_id))
    conn.commit()

def get_donation(donation_id):
    """Получает информацию о донате"""
    cursor.execute('SELECT * FROM donations WHERE id = ?', (donation_id,))
    return cursor.fetchone()

def update_donation_payment_link(donation_id, payment_link):
    """Обновляет ссылку на оплату доната"""
    cursor.execute('UPDATE donations SET payment_link = ? WHERE id = ?', (payment_link, donation_id))
    conn.commit()

print("✅ Модуль database.py загружен")
