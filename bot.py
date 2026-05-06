import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database import *

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== СОСТОЯНИЯ ==========
class AdminStates(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_name = State()
    waiting_channel_stars = State()
    waiting_balance_user = State()
    waiting_balance_amount = State()
    waiting_ban_user = State()
    waiting_broadcast = State()
    waiting_withdraw_amount = State()
    waiting_giveaway_title = State()
    waiting_giveaway_prize = State()
    waiting_giveaway_end_date = State()
    waiting_giveaway_channels = State()
    waiting_check_user = State()
    waiting_edit_giveaway_id = State()
    waiting_edit_giveaway_field = State()
    waiting_edit_giveaway_value = State()

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_subscription(user_id):
    """Проверяет подписку на обязательный канал"""
    try:
        member = await bot.get_chat_member(chat_id=f"@{config.REQUIRED_CHANNEL}", user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        if member.status == 'restricted' and member.is_member:
            return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки для {user_id}: {e}")
        return False

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="💸 Вывод Stars", callback_data="withdraw")],
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="🎁 Розыгрыши", callback_data="giveaways")],
        [InlineKeyboardButton(text="🎲 Мини-игра Фортуна", callback_data="fortune")],
        [InlineKeyboardButton(text="⭐ Ежедневный бонус", callback_data="daily")],
        [InlineKeyboardButton(text="⚡ Ежечасный бонус", callback_data="hourly")]
    ])

def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🗑 Удалить канал", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="📝 Список каналов", callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="💰 Выдать чек", callback_data="admin_give_balance")],
        [InlineKeyboardButton(text="🔨 Бан/Разбан", callback_data="admin_ban_menu")],
        [InlineKeyboardButton(text="✅ Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎁 Управление конкурсами", callback_data="admin_manage_giveaways")],
        [InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="admin_check_user")]
    ])

def manage_giveaways_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать конкурс", callback_data="admin_create_giveaway")],
        [InlineKeyboardButton(text="✏️ Изменить конкурс", callback_data="admin_edit_giveaway")],
        [InlineKeyboardButton(text="🗑 Удалить конкурс", callback_data="admin_delete_giveaway")],
        [InlineKeyboardButton(text="📋 Список конкурсов", callback_data="admin_list_giveaways")],
        [InlineKeyboardButton(text="🎲 Завершить и выбрать победителя", callback_data="admin_end_giveaway")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    first_name = msg.from_user.first_name
    last_name = msg.from_user.last_name
    
    user = get_user(user_id)
    if user and user['is_banned'] == 1:
        await msg.answer("🚫 Вы заблокированы!")
        return
    
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if ref == user_id:
        ref = None
    
    add_user(user_id, username, first_name, last_name, ref)
    
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=f"https://t.me/{config.REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_sub")]
        ])
        await msg.answer(
            f"⚠️ *Для использования бота необходимо подписаться на канал!*\n\n"
            f"👉 *Канал:* [{config.REQUIRED_CHANNEL}](https://t.me/{config.REQUIRED_CHANNEL})\n\n"
            f"После подписки нажмите «Проверить подписку»",
            parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True
        )
        return
    
    await msg.answer(
        "✨ *Добро пожаловать!* ✨\n\n"
        "💰 *Как заработать Stars:*\n"
        "• 📋 Подпишись на каналы → +0.25⭐ за каждый\n"
        "• 👥 Приглашай друзей → +3⭐ за 3 задания друга\n"
        "• ⭐ Ежедневный бонус → +1⭐\n"
        "• ⚡ Ежечасный бонус → +0.25⭐\n"
        "• 🎲 Фортуна → Выиграй 25⭐\n\n"
        "💸 *Вывод от 15⭐*\n"
        "🎁 *Регулярные розыгрыши призов!*",
        reply_markup=main_menu(), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_sub")
async def check_subscription_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if await check_subscription(user_id):
        await call.message.edit_text("✅ Спасибо за подписку! Добро пожаловать в бот.", reply_markup=main_menu())
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=f"https://t.me/{config.REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_sub")]
        ])
        await call.message.edit_text(
            f"❌ Вы не подписаны на канал!\n\n"
            f"👉 [Подпишитесь на {config.REQUIRED_CHANNEL}](https://t.me/{config.REQUIRED_CHANNEL})",
            parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True
        )

@dp.message(Command("admin"))
async def admin(msg: types.Message):
    if msg.from_user.id == config.ADMIN_ID:
        await msg.answer("🛠 *Админ-панель*", parse_mode="Markdown", reply_markup=admin_panel())

# ========== ЗАДАНИЯ ==========
@dp.callback_query(F.data == "tasks")
async def show_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    user = get_user(user_id)
    if user and user['is_banned'] == 1:
        await call.answer("Вы заблокированы!", show_alert=True)
        return
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    channels = get_channels()
    if not channels:
        await call.message.edit_text("❌ Заданий пока нет.", reply_markup=main_menu())
        return
    
    text = "📢 *Подпишись на каналы и нажми ✅ Готово:*\n\n"
    buttons = []
    
    for ch in channels:
        channel_id, name, stars = ch
        if is_completed(user_id, channel_id):
            text += f"✅ {name} - выполнено (+{stars}⭐)\n"
        else:
            text += f"📌 {name} (+{stars}⭐)\n"
            buttons.append([InlineKeyboardButton(text=f"🔗 Подписаться на {name}", url=f"https://t.me/{channel_id}")])
            buttons.append([InlineKeyboardButton(text=f"✅ Готово (+{stars}⭐)", callback_data=f"complete_{channel_id}_{stars}")])
    
    if buttons:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    else:
        await call.message.edit_text("🎉 Ты выполнил все задания!", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("complete_"))
async def complete_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split("_")
    channel_id = parts[1]
    stars = float(parts[2])
    
    if not await check_subscription(user_id):
        await call.answer("❌ Вы отписались от обязательного канала!", show_alert=True)
        return
    
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel_id}", user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await call.answer("❌ Вы не подписаны на этот канал!", show_alert=True)
            return
    except:
        await call.answer("❌ Не удалось проверить подписку", show_alert=True)
        return
    
    if is_completed(user_id, channel_id):
        await call.answer("❌ Ты уже получил Stars за этот канал!", show_alert=True)
        return
    
    mark_completed(user_id, channel_id, stars)
    update_balance(user_id, stars, f"Подписка на канал {channel_id}")
    
    completed_count = get_completed_count(user_id)
    user = get_user(user_id)
    if completed_count == 3 and user and user['ref_by']:
        update_balance(user['ref_by'], 3, f"Реферальный бонус за {user_id}")
        try:
            await bot.send_message(user['ref_by'], f"🎉 Ваш друг выполнил 3 задания! Вы получили +3⭐")
        except:
            pass
    
    await call.answer(f"+{stars}⭐", show_alert=True)
    await call.message.edit_text("✅ Готово! Возвращайся в меню.", reply_markup=main_menu())

# ========== БАЛАНС ==========
@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.answer("Ошибка", show_alert=True)
        return
    
    await call.message.edit_text(
        f"⭐ *Твой баланс:* {user['balance']} Stars\n"
        f"👥 *Приглашено друзей:* {user['referrals']}\n"
        f"📋 *Выполнено заданий:* {user['tasks_completed']}\n"
        f"💰 *Всего заработано:* {user['total_earned']} Stars\n"
        f"💸 *Всего выведено:* {user['total_withdrawn']} Stars\n"
        f"💸 *Минимальный вывод:* 15 Stars",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== ВЫВОД ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    if not user or user['is_banned'] == 1:
        await call.answer("Доступ запрещён", show_alert=True)
        return
    
    if not await check_subscription(call.from_user.id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if user['balance'] < 15:
        await call.answer("❌ Недостаточно Stars. Нужно минимум 15⭐", show_alert=True)
        return
    
    await call.message.edit_text("💸 *Введите сумму для вывода:*\n(Минимум 15⭐, максимум весь баланс)", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_withdraw_amount)

@dp.message(AdminStates.waiting_withdraw_amount)
async def process_withdraw(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        user_id = msg.from_user.id
        username = msg.from_user.username or str(user_id)
        user = get_user(user_id)
        
        if amount < 15:
            await msg.answer("❌ Минимальная сумма вывода - 15⭐")
            return
        
        if user['balance'] < amount:
            await msg.answer(f"❌ Недостаточно Stars. Ваш баланс: {user['balance']}⭐")
            return
        
        add_withdrawal(user_id, username, amount)
        update_balance(user_id, -amount, f"Заявка на вывод {amount}⭐")
        await msg.answer(f"✅ Заявка на вывод {amount}⭐ отправлена администратору!\nОжидайте обработки.", reply_markup=main_menu())
        await state.clear()
        
        await bot.send_message(config.ADMIN_ID, f"📨 *Новая заявка на вывод!*\nОт: @{username} ({user_id})\nСумма: {amount}⭐", parse_mode="Markdown")
        
    except ValueError:
        await msg.answer("❌ Введите число (например: 15 или 20.5)")

# ========== РЕФЕРАЛКА ==========
@dp.callback_query(F.data == "referral")
async def referral(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    user = get_user(user_id)
    
    await call.message.edit_text(
        f"👥 *Приглашай друзей и зарабатывай!*\n\n"
        f"🔗 Твоя реферальная ссылка:\n`{link}`\n\n"
        f"📌 *Как это работает:*\n"
        f"• Друг переходит по ссылке\n"
        f"• Выполняет 3 любых задания\n"
        f"• Ты получаешь +3⭐\n\n"
        f"👥 *Приглашено:* {user['referrals'] if user else 0} друзей",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== БОНУСЫ ==========
@dp.callback_query(F.data == "daily")
async def daily_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if can_claim_daily(user_id):
        update_balance(user_id, 1.0, "Ежедневный бонус")
        set_daily_claimed(user_id)
        await call.answer("✅ +1⭐ (ежедневный бонус)", show_alert=True)
        await call.message.edit_text("⭐ Бонус получен! Возвращайся завтра.", reply_markup=main_menu())
    else:
        await call.answer("❌ Бонус уже получен сегодня! Возвращайся завтра.", show_alert=True)

@dp.callback_query(F.data == "hourly")
async def hourly_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if can_claim_hourly(user_id):
        update_balance(user_id, 0.25, "Ежечасный бонус")
        set_hourly_claimed(user_id)
        await call.answer("✅ +0.25⭐ (ежечасный бонус)", show_alert=True)
        await call.message.edit_text("⚡ Бонус получен! Возвращайся через час.", reply_markup=main_menu())
    else:
        await call.answer("❌ Бонус уже получен! Возвращайся через час.", show_alert=True)

# ========== ФОРТУНА ==========
@dp.callback_query(F.data == "fortune")
async def fortune_game(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if user['balance'] < 5:
        await call.answer("❌ Недостаточно Stars! Нужно 5⭐ для игры.", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Крутить! (5⭐)", callback_data="spin_fortune")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    
    await call.message.edit_text(
        "🎲 *ФОРТУНА* 🎲\n\n"
        "Правила:\n"
        "• Стоимость прокрутки: 5⭐\n"
        "• Шанс выигрыша: 20% (1 из 5)\n"
        "• Выигрыш: 25⭐\n\n"
        "Готов рискнуть?",
        parse_mode="Markdown", reply_markup=keyboard
    )

@dp.callback_query(F.data == "spin_fortune")
async def spin_fortune(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if user['balance'] < 5:
        await call.answer("❌ Недостаточно Stars!", show_alert=True)
        return
    
    update_balance(user_id, -5, "Игра Фортуна (ставка)")
    
    is_win = random.randint(1, 5) == 1
    
    if is_win:
        update_balance(user_id, 25, "Игра Фортуна (выигрыш)")
        add_game_result(user_id, True)
        result_text = "🎉 *ПОБЕДА!* 🎉\n\nВы выиграли 25⭐!"
    else:
        add_game_result(user_id, False)
        result_text = "😢 *ПРОИГРЫШ* 😢\n\nВы проиграли 5⭐.\nПопробуйте снова!"
    
    stats = get_game_stats(user_id)
    user = get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Сыграть ещё", callback_data="fortune")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ])
    
    await call.message.edit_text(
        f"{result_text}\n\n"
        f"⭐ Ваш баланс: {user['balance']} Stars\n"
        f"📊 Статистика: {stats[0] if stats else 0} игр, {stats[1] if stats else 0} побед",
        parse_mode="Markdown", reply_markup=keyboard
    )

# ========== РОЗЫГРЫШИ (ДЛЯ ПОЛЬЗОВАТЕЛЕЙ) ==========
@dp.callback_query(F.data == "giveaways")
async def show_giveaways(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    giveaways = get_active_giveaways()
    if not giveaways:
        await call.answer("❌ Активных розыгрышей нет", show_alert=True)
        return
    
    text = "🎁 *Активные розыгрыши:*\n\n"
    buttons = []
    
    for g in giveaways:
        g_id = g[0]
        title = g[1]
        prize = g[2]
        end_date = g[3]
        participants_count = g[12]
        
        end = datetime.fromisoformat(end_date)
        remaining = end - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        text += f"📌 *{title}*\n🏆 Приз: {prize}\n👥 Участников: {participants_count}\n⏰ Осталось: {hours}ч {minutes}мин\n\n"
        buttons.append([InlineKeyboardButton(text=f"🎲 Участвовать в {title[:20]}", callback_data=f"join_giveaway_{g_id}")])
    
    if buttons:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("join_giveaway_"))
async def join_giveaway(call: types.CallbackQuery):
    user_id = call.from_user.id
    giveaway_id = int(call.data.split("_")[2])
    giveaway = get_giveaway(giveaway_id)
    username = call.from_user.username or str(user_id)
    
    if not giveaway:
        await call.answer("Розыгрыш не найден", show_alert=True)
        return
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    required = giveaway[4]
    if required:
        channels = required.split(',')
        for ch in channels:
            if ch.strip():
                try:
                    member = await bot.get_chat_member(chat_id=f"@{ch.strip()}", user_id=user_id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        await call.answer(f"❌ Подпишитесь на канал @{ch}", show_alert=True)
                        return
                except:
                    await call.answer(f"❌ Не удалось проверить подписку на @{ch}", show_alert=True)
                    return
    
    add_participant(giveaway_id, user_id, username)
    await call.answer("✅ Вы участвуете в розыгрыше! Удачи!", show_alert=True)

# ========== АДМИН: УПРАВЛЕНИЕ КОНКУРСАМИ ==========
@dp.callback_query(F.data == "admin_manage_giveaways")
async def manage_giveaways(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.edit_text("🎁 *Управление конкурсами*", parse_mode="Markdown", reply_markup=manage_giveaways_menu())

@dp.callback_query(F.data == "admin_create_giveaway")
async def create_giveaway_step1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("📝 Введите название розыгрыша:")
    await state.set_state(AdminStates.waiting_giveaway_title)

@dp.message(AdminStates.waiting_giveaway_title)
async def create_giveaway_step2(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await msg.answer("🏆 Введите приз (например: 100⭐ или iPhone 15):")
    await state.set_state(AdminStates.waiting_giveaway_prize)

@dp.message(AdminStates.waiting_giveaway_prize)
async def create_giveaway_step3(msg: types.Message, state: FSMContext):
    await state.update_data(prize=msg.text)
    await msg.answer("📅 Введите дату окончания (ГГГГ-ММ-ДД ЧЧ:ММ):\nПример: 2025-12-31 23:59")
    await state.set_state(AdminStates.waiting_giveaway_end_date)

@dp.message(AdminStates.waiting_giveaway_end_date)
async def create_giveaway_step4(msg: types.Message, state: FSMContext):
    try:
        end_date = datetime.strptime(msg.text, "%Y-%m-%d %H:%M")
        await state.update_data(end_date=end_date.isoformat())
        await msg.answer("📢 Введите каналы спонсоров (через запятую, без @):\nПример: channel1,channel2\nИли 0 если без подписки:")
        await state.set_state(AdminStates.waiting_giveaway_channels)
    except ValueError:
        await msg.answer("❌ Неверный формат! Используйте: ГГГГ-ММ-ДД ЧЧ:ММ")

@dp.message(AdminStates.waiting_giveaway_channels)
async def create_giveaway_step5(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    channels = msg.text if msg.text != "0" else ""
    
    giveaway_id = add_giveaway(data['title'], data['prize'], data['end_date'], channels, config.ADMIN_ID)
    
    text = (
        f"🎉 *НОВЫЙ РОЗЫГРЫШ!* 🎉\n\n"
        f"📌 *{data['title']}*\n"
        f"🏆 Приз: {data['prize']}\n"
        f"⏰ Заканчивается: {data['end_date'][:16]}\n\n"
        f"👉 Участвовать в боте: @{config.REQUIRED_CHANNEL}\n"
    )
    
    if channels:
        text += f"\n📢 *Обязательная подписка:*\n"
        for ch in channels.split(','):
            if ch.strip():
                text += f"• @{ch.strip()}\n"
    
    try:
        sent = await bot.send_message(f"@{config.REQUIRED_CHANNEL}", text, parse_mode="Markdown")
        set_giveaway_message_id(giveaway_id, sent.message_id)
    except Exception as e:
        print(f"Ошибка отправки в канал: {e}")
    
    await msg.answer(f"✅ Розыгрыш «{data['title']}» создан!", reply_markup=manage_giveaways_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_list_giveaways")
async def list_all_giveaways(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    giveaways = get_all_giveaways(include_inactive=True)
    if not giveaways:
        await call.answer("Нет конкурсов", show_alert=True)
        return
    
    text = "📋 *Все конкурсы:*\n\n"
    for g in giveaways:
        g_id = g[0]
        title = g[1]
        prize = g[2]
        end_date = g[3]
        is_active = g[5]
        participants_count = g[12]
        status = "🟢 Активен" if is_active else "🔴 Завершен"
        text += f"#{g_id} *{title}*\n🏆 {prize}\n📅 До: {end_date[:16]}\n{status}\n👥 {participants_count} участников\n\n"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=manage_giveaways_menu())

@dp.callback_query(F.data == "admin_delete_giveaway")
async def delete_giveaway_select(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    giveaways = get_all_giveaways(include_inactive=True)
    if not giveaways:
        await call.answer("Нет конкурсов для удаления", show_alert=True)
        return
    
    buttons = []
    for g in giveaways:
        g_id = g[0]
        title = g[1]
        buttons.append([InlineKeyboardButton(text=f"🗑 {title[:30]}", callback_data=f"del_giveaway_{g_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_giveaways")])
    
    await call.message.edit_text("🗑 *Выберите конкурс для удаления:*", parse_mode="Markdown", 
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("del_giveaway_"))
async def confirm_delete_giveaway(call: types.CallbackQuery):
    giveaway_id = int(call.data.split("_")[2])
    giveaway = get_giveaway(giveaway_id)
    
    if not giveaway:
        await call.answer("Конкурс не найден", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{giveaway_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_manage_giveaways")]
    ])
    
    await call.message.edit_text(f"⚠️ *Удалить конкурс «{giveaway[1]}»?*\nЭто действие необратимо!", 
                                  parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("confirm_del_"))
async def execute_delete_giveaway(call: types.CallbackQuery):
    giveaway_id = int(call.data.split("_")[2])
    delete_giveaway(giveaway_id)
    await call.answer("✅ Конкурс удалён", show_alert=True)
    await call.message.edit_text("🗑 Конкурс успешно удалён!", reply_markup=manage_giveaways_menu())

@dp.callback_query(F.data == "admin_edit_giveaway")
async def edit_giveaway_select(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    giveaways = get_all_giveaways(include_inactive=True)
    if not giveaways:
        await call.answer("Нет конкурсов для изменения", show_alert=True)
        return
    
    buttons = []
    for g in giveaways:
        g_id = g[0]
        title = g[1]
        buttons.append([InlineKeyboardButton(text=f"✏️ {title[:30]}", callback_data=f"edit_giveaway_{g_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_giveaways")])
    
    await call.message.edit_text("✏️ *Выберите конкурс для изменения:*", parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("edit_giveaway_"))
async def edit_giveaway_field(call: types.CallbackQuery, state: FSMContext):
    giveaway_id = int(call.data.split("_")[2])
    await state.update_data(edit_giveaway_id=giveaway_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data="edit_field_title")],
        [InlineKeyboardButton(text="🏆 Приз", callback_data="edit_field_prize")],
        [InlineKeyboardButton(text="📅 Дата окончания", callback_data="edit_field_end_date")],
        [InlineKeyboardButton(text="📢 Каналы спонсоров", callback_data="edit_field_channels")],
        [InlineKeyboardButton(text="🔴 Завершить конкурс", callback_data="edit_field_end")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_giveaways")]
    ])
    
    giveaway = get_giveaway(giveaway_id)
    await call.message.edit_text(f"✏️ *Редактирование конкурса:*\n\n"
                                  f"📌 Название: {giveaway[1]}\n"
                                  f"🏆 Приз: {giveaway[2]}\n"
                                  f"📅 До: {giveaway[3][:16]}\n"
                                  f"📢 Каналы: {giveaway[4] or 'нет'}\n\n"
                                  f"*Выберите поле для изменения:*",
                                  parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("edit_field_"))
async def edit_giveaway_value(call: types.CallbackQuery, state: FSMContext):
    field = call.data.split("_")[2]
    
    if field == 'end':
        data = await state.get_data()
        giveaway_id = data['edit_giveaway_id']
        update_giveaway(giveaway_id, is_active=0)
        await call.answer("✅ Конкурс завершён", show_alert=True)
        await call.message.edit_text("✅ Конкурс завершён!", reply_markup=manage_giveaways_menu())
        await state.clear()
        return
    
    await state.update_data(edit_field=field)
    
    prompts = {
        'title': 'Введите новое название конкурса:',
        'prize': 'Введите новый приз:',
        'end_date': 'Введите новую дату (ГГГГ-ММ-ДД ЧЧ:ММ):',
        'channels': 'Введите новые каналы (через запятую, без @) или 0:'
    }
    
    await call.message.answer(prompts.get(field, 'Введите новое значение:'))
    await state.set_state(AdminStates.waiting_edit_giveaway_value)

@dp.message(AdminStates.waiting_edit_giveaway_value)
async def save_edited_giveaway_value(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    giveaway_id = data['edit_giveaway_id']
    field = data['edit_field']
    value = msg.text.strip()
    
    if field == 'end_date':
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M")
        except:
            await msg.answer("❌ Неверный формат! Используйте: ГГГГ-ММ-ДД ЧЧ:ММ")
            return
    elif field == 'channels' and value == '0':
        value = ''
    
    update_giveaway(giveaway_id, **{field: value})
    await msg.answer("✅ Конкурс успешно обновлён!", reply_markup=manage_giveaways_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_end_giveaway")
async def end_giveaway_select(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    giveaways = get_active_giveaways()
    if not giveaways:
        await call.answer("Нет активных конкурсов", show_alert=True)
        return
    
    buttons = []
    for g in giveaways:
        g_id = g[0]
        title = g[1]
        participants = g[12]
        if participants > 0:
            buttons.append([InlineKeyboardButton(text=f"🎲 Завершить {title[:25]} ({participants} уч.)", callback_data=f"end_giveaway_{g_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_giveaways")])
    
    if not buttons:
        await call.answer("Нет конкурсов с участниками", show_alert=True)
        return
    
    await call.message.edit_text("🎲 *Выберите конкурс для завершения и выбора победителя:*", 
                                  parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("end_giveaway_"))
async def execute_end_giveaway(call: types.CallbackQuery):
    giveaway_id = int(call.data.split("_")[2])
    giveaway = get_giveaway(giveaway_id)
    participants = get_participants(giveaway_id)
    
    if not participants:
        await call.answer("Нет участников в конкурсе!", show_alert=True)
        return
    
    winner = random.choice(participants)
    winner_id, winner_username = winner
    
    end_giveaway(giveaway_id, winner_id, winner_username)
    
    prize_text = giveaway[2]
    if '⭐' in prize_text:
        try:
            prize_amount = float(prize_text.replace('⭐', '').strip())
            update_balance(winner_id, prize_amount, f"Выигрыш в конкурсе {giveaway[1]}")
        except:
            pass
    
    try:
        await bot.send_message(winner_id, f"🎉 *ПОЗДРАВЛЯЕМ!* 🎉\n\nВы выиграли в конкурсе «{giveaway[1]}»!\n🏆 Ваш приз: {giveaway[2]}\n\nСвяжитесь с администратором для получения!", parse_mode="Markdown")
    except:
        pass
    
    await call.answer(f"✅ Победитель: @{winner_username}", show_alert=True)
    await call.message.edit_text(f"🎉 *Конкурс завершён!*\n\nПобедитель: @{winner_username}\nПриз: {giveaway[2]}", 
                                  parse_mode="Markdown", reply_markup=manage_giveaways_menu())

# ========== АДМИН: ОСТАЛЬНЫЕ ФУНКЦИИ ==========
@dp.callback_query(F.data == "admin_add_channel")
async def add_channel_step1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("📎 Введите username канала (без @):")
    await state.set_state(AdminStates.waiting_channel_id)

@dp.message(AdminStates.waiting_channel_id)
async def add_channel_step2(msg: types.Message, state: FSMContext):
    await state.update_data(channel_id=msg.text.strip())
    await msg.answer("📝 Введите название канала:")
    await state.set_state(AdminStates.waiting_channel_name)

@dp.message(AdminStates.waiting_channel_name)
async def add_channel_step3(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await msg.answer("⭐ Введите Stars за подписку (0.25):")
    await state.set_state(AdminStates.waiting_channel_stars)

@dp.message(AdminStates.waiting_channel_stars)
async def add_channel_step4(msg: types.Message, state: FSMContext):
    try:
        stars = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        add_channel(data['channel_id'], data['name'], stars, config.ADMIN_ID)
        await msg.answer(f"✅ Канал «{data['name']}» добавлен! Награда: {stars}⭐")
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число")

@dp.callback_query(F.data == "admin_list_channels")
async def list_channels(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    channels = get_all_channels()
    text = "📋 *Все каналы:*\n\n"
    for ch in channels:
        ch_id = ch[1]
        name = ch[2]
        stars = ch[3]
        is_required = ch[4]
        required = "🔒 ОБЯЗАТЕЛЬНЫЙ" if is_required else "📌 Обычный"
        text += f"• {name}: @{ch_id} | {stars}⭐ | {required}\n"
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())

@dp.callback_query(F.data == "admin_del_channel")
async def delete_channel_menu(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    channels = get_channels()
    if not channels:
        await call.answer("Нет каналов для удаления", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=f"❌ {ch[1]}", callback_data=f"delch_{ch[0]}")] for ch in channels]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    await call.message.edit_text("🗑 Выберите канал для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("delch_"))
async def confirm_delete_channel(call: types.CallbackQuery):
    channel_id = call.data.split("_")[1]
    delete_channel(channel_id)
    await call.answer("✅ Канал удалён", show_alert=True)
    await call.message.delete()

@dp.callback_query(F.data == "admin_give_balance")
async def give_balance_step1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🔍 Введите @username пользователя или его ID:")
    await state.set_state(AdminStates.waiting_balance_user)

@dp.message(AdminStates.waiting_balance_user)
async def give_balance_step2(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    if query.startswith('@'):
        user = get_user_by_username(query[1:])
    else:
        try:
            user = get_user(int(query))
        except:
            user = None
    
    if not user:
        await msg.answer("❌ Пользователь не найден!")
        await state.clear()
        return
    
    await state.update_data(target_user=user['user_id'])
    await msg.answer(f"💰 Введите сумму для начисления @{user['username'] or user['user_id']}:\nТекущий баланс: {user['balance']}⭐")
    await state.set_state(AdminStates.waiting_balance_amount)

@dp.message(AdminStates.waiting_balance_amount)
async def give_balance_step3(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data['target_user']
        update_balance(user_id, amount, f"Начислено администратором")
        user = get_user(user_id)
        await msg.answer(f"✅ Начислено {amount}⭐ пользователю @{user['username'] or user_id}\nНовый баланс: {user['balance']}⭐")
        try:
            await bot.send_message(user_id, f"💰 Администратор начислил вам {amount}⭐!\nВаш баланс: {user['balance']}⭐")
        except:
            pass
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число")

@dp.callback_query(F.data == "admin_withdrawals")
async def show_withdrawals(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    requests = get_pending_withdrawals()
    if not requests:
        await call.answer("Нет активных заявок", show_alert=True)
        return
    for req in requests:
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выплачено", callback_data=f"approve_{req[0]}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{req[0]}")]
        ])
        await call.message.answer(f"📨 *Заявка #{req[0]}*\nОт: @{req[2]} ({req[1]})\nСумма: {req[3]}⭐\nДата: {req[5][:16]}", 
                                  parse_mode="Markdown", reply_markup=buttons)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdrawal(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_withdrawal_status(req_id, "approved", config.ADMIN_ID)
        try:
            await bot.send_message(req[0], f"✅ Ваша заявка на вывод {req[1]}⭐ одобрена!")
        except:
            pass
        await call.answer("✅ Выплачено", show_alert=True)
        await call.message.delete()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_withdrawal(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_balance(req[0], req[1], "Возврат после отклонения вывода")
        update_withdrawal_status(req_id, "rejected", config.ADMIN_ID, "Отклонено администратором")
        try:
            await bot.send_message(req[0], f"❌ Ваша заявка на вывод {req[1]}⭐ отклонена. Средства возвращены.")
        except:
            pass
        await call.answer("❌ Отклонено", show_alert=True)
        await call.message.delete()

@dp.callback_query(F.data == "admin_ban_menu")
async def ban_menu(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🔨 Введите @username или user_id для блокировки/разблокировки:")
    await state.set_state(AdminStates.waiting_ban_user)

@dp.message(AdminStates.waiting_ban_user)
async def process_ban(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    if query.startswith('@'):
        user = get_user_by_username(query[1:])
    else:
        try:
            user = get_user(int(query))
        except:
            user = None
    
    if not user:
        await msg.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    if user['is_banned'] == 1:
        unban_user(user['user_id'])
        await msg.answer(f"✅ Пользователь @{user['username'] or user['user_id']} разблокирован")
    else:
        ban_user(user['user_id'])
        await msg.answer(f"✅ Пользователь @{user['username'] or user['user_id']} заблокирован")
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("📢 Введите текст рассылки:")
    await state.set_state(AdminStates.waiting_broadcast)

@dp.message(AdminStates.waiting_broadcast)
async def send_broadcast(msg: types.Message, state: FSMContext):
    text = msg.text
    users = get_all_users()
    success = 0
    fail = 0
    
    status_msg = await msg.answer("📤 Идёт рассылка...")
    
    for user_id, username in users:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\n📨 Доставлено: {success}\n❌ Ошибок: {fail}")
    await state.clear()

@dp.callback_query(F.data == "admin_check_user")
async def check_user_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🔍 Введите @username или ID пользователя:")
    await state.set_state(AdminStates.waiting_check_user)

@dp.message(AdminStates.waiting_check_user)
async def check_user_result(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    
    if query.startswith('@'):
        user = get_user_by_username(query[1:])
    else:
        try:
            user = get_user(int(query))
        except:
            user = None
    
    if not user:
        await msg.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    is_subbed = await check_subscription(user['user_id'])
    
    text = (
        f"🔍 *Информация о пользователе*\n\n"
        f"🆔 ID: `{user['user_id']}`\n"
        f"📝 Username: @{user['username'] or 'нет'}\n"
        f"👤 Имя: {user['first_name'] or 'нет'}\n"
        f"⭐ Баланс: {user['balance']} Stars\n"
        f"🚫 Статус: {'Заблокирован' if user['is_banned'] else 'Активен'}\n"
        f"👥 Рефералов: {user['referrals']}\n"
        f"📋 Выполнено заданий: {user['tasks_completed']}\n"
        f"💰 Всего заработано: {user['total_earned']} Stars\n"
        f"💸 Всего выведено: {user['total_withdrawn']} Stars\n"
        f"📅 Дата регистрации: {user['register_date'][:16] if user['register_date'] else 'нет'}\n\n"
        f"📢 *Обязательный канал:*\n"
        f"{'✅ Подписан' if is_subbed else '❌ НЕ ПОДПИСАН'}"
    )
    
    await msg.answer(text, parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_back")
async def back_to_admin(call: types.CallbackQuery):
    await call.message.edit_text("🛠 *Админ-панель*", parse_mode="Markdown", reply_markup=admin_panel())

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text("✨ *Главное меню*", parse_mode="Markdown", reply_markup=main_menu())

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("🤖 Бот запущен!")
    print(f"✅ Обязательный канал: @{config.REQUIRED_CHANNEL}")
    print(f"✅ Админ ID: {config.ADMIN_ID}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
