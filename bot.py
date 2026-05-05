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

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_subscription(user_id):
    """Проверяет подписку на обязательный канал"""
    try:
        # Пробуем получить информацию о пользователе в канале
        member = await bot.get_chat_member(chat_id=f"@{config.REQUIRED_CHANNEL}", user_id=user_id)
        
        # Статусы, которые считаются подпиской
        if member.status in ['member', 'administrator', 'creator']:
            return True
        if member.status == 'restricted' and member.is_member:
            return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки для {user_id}: {e}")
        # Если ошибка - считаем что не подписан (безопаснее)
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
        [InlineKeyboardButton(text="🎁 Создать розыгрыш", callback_data="admin_create_giveaway")],
        [InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="admin_check_user")]
    ])

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    
    # Проверка на бан
    user = get_user(user_id)
    if user and user[3] == 1:
        await msg.answer("🚫 Вы заблокированы!")
        return
    
    # Реферальная система
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if ref == user_id:
        ref = None
    
    add_user(user_id, username, ref)
    
    # Проверка подписки на обязательный канал
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
        # Показываем кнопку снова
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
    if user and user[3] == 1:
        await call.answer("Вы заблокированы!", show_alert=True)
        return
    
    # Проверка подписки на обязательный канал
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
        ch_id, name, stars = ch[1], ch[2], ch[3]
        if is_completed(user_id, ch_id):
            text += f"✅ {name} - выполнено (+{stars}⭐)\n"
        else:
            text += f"📌 {name} (+{stars}⭐)\n"
            buttons.append([InlineKeyboardButton(text=f"🔗 Подписаться на {name}", url=f"https://t.me/{ch_id}")])
            buttons.append([InlineKeyboardButton(text=f"✅ Готово (+{stars}⭐)", callback_data=f"complete_{ch_id}_{stars}")])
    
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
    
    # Проверка подписки на обязательный канал
    if not await check_subscription(user_id):
        await call.answer("❌ Вы отписались от обязательного канала!", show_alert=True)
        return
    
    # Проверка подписки на канал задания
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel_id}", user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await call.answer("❌ Вы не подписаны на этот канал!", show_alert=True)
            return
    except Exception as e:
        print(f"Ошибка проверки канала {channel_id}: {e}")
        await call.answer("❌ Не удалось проверить подписку", show_alert=True)
        return
    
    if is_completed(user_id, channel_id):
        await call.answer("❌ Ты уже получил Stars за этот канал!", show_alert=True)
        return
    
    mark_completed(user_id, channel_id)
    update_balance(user_id, stars)
    
    # Реферальный бонус (после 3 заданий)
    completed_count = get_completed_count(user_id)
    user = get_user(user_id)
    if completed_count == 3 and user and user[5]:
        update_balance(user[5], 3)
        try:
            await bot.send_message(user[5], f"🎉 Ваш друг выполнил 3 задания! Вы получили +3⭐")
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
        f"⭐ *Твой баланс:* {user[2]} Stars\n"
        f"👥 *Приглашено друзей:* {user[4]}\n"
        f"📋 *Выполнено заданий:* {user[6]}\n"
        f"💸 *Минимальный вывод:* 15 Stars",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== ВЫВОД ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    if not user or user[3] == 1:
        await call.answer("Доступ запрещён", show_alert=True)
        return
    
    if not await check_subscription(call.from_user.id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if user[2] < 15:
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
        
        if user[2] < amount:
            await msg.answer(f"❌ Недостаточно Stars. Ваш баланс: {user[2]}⭐")
            return
        
        add_withdrawal(user_id, username, amount)
        update_balance(user_id, -amount)
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
    
    await call.message.edit_text(
        f"👥 *Приглашай друзей и зарабатывай!*\n\n"
        f"🔗 Твоя реферальная ссылка:\n`{link}`\n\n"
        f"📌 *Как это работает:*\n"
        f"• Друг переходит по ссылке\n"
        f"• Выполняет 3 любых задания\n"
        f"• Ты получаешь +3⭐\n\n"
        f"👥 *Приглашено:* {get_user(user_id)[4]} друзей",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== ЕЖЕДНЕВНЫЙ БОНУС ==========
@dp.callback_query(F.data == "daily")
async def daily_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if can_claim_daily(user_id):
        update_balance(user_id, 1.0)
        set_daily_claimed(user_id)
        await call.answer("✅ +1⭐ (ежедневный бонус)", show_alert=True)
        await call.message.edit_text("⭐ Бонус получен! Возвращайся завтра.", reply_markup=main_menu())
    else:
        await call.answer("❌ Бонус уже получен сегодня! Возвращайся завтра.", show_alert=True)

# ========== ЕЖЕЧАСНЫЙ БОНУС ==========
@dp.callback_query(F.data == "hourly")
async def hourly_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if can_claim_hourly(user_id):
        update_balance(user_id, 0.25)
        set_hourly_claimed(user_id)
        await call.answer("✅ +0.25⭐ (ежечасный бонус)", show_alert=True)
        await call.message.edit_text("⚡ Бонус получен! Возвращайся через час.", reply_markup=main_menu())
    else:
        await call.answer("❌ Бонус уже получен! Возвращайся через час.", show_alert=True)

# ========== МИНИ-ИГРА ФОРТУНА ==========
@dp.callback_query(F.data == "fortune")
async def fortune_game(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    if user[2] < 5:
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
    
    if user[2] < 5:
        await call.answer("❌ Недостаточно Stars!", show_alert=True)
        return
    
    # Списываем 5⭐
    update_balance(user_id, -5)
    
    # Генерация результата (1 выигрыш из 5)
    is_win = random.randint(1, 5) == 1
    
    if is_win:
        update_balance(user_id, 25)
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
        f"⭐ Ваш баланс: {user[2]} Stars\n"
        f"📊 Статистика: {stats[0] if stats else 0} игр, {stats[1] if stats else 0} побед",
        parse_mode="Markdown", reply_markup=keyboard
    )

# ========== РОЗЫГРЫШИ ==========
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
        g_id, title, prize, end_date, req_channels, _, _, _, _ = g
        end = datetime.fromisoformat(end_date)
        remaining = end - datetime.now()
        hours = remaining.total_seconds() // 3600
        
        text += f"📌 *{title}*\n🏆 Приз: {prize}\n⏰ Осталось: {int(hours)} ч.\n\n"
        buttons.append([InlineKeyboardButton(text=f"🎲 Участвовать в {title}", callback_data=f"join_giveaway_{g_id}")])
    
    if buttons:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("join_giveaway_"))
async def join_giveaway(call: types.CallbackQuery):
    user_id = call.from_user.id
    giveaway_id = int(call.data.split("_")[2])
    giveaway = get_giveaway(giveaway_id)
    
    if not giveaway:
        await call.answer("Розыгрыш не найден", show_alert=True)
        return
    
    # Проверка подписки на обязательный канал
    if not await check_subscription(user_id):
        await call.answer("❌ Подпишитесь на обязательный канал!", show_alert=True)
        return
    
    # Проверка подписки на каналы спонсоров
    required = giveaway[5]
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
    
    add_participant(giveaway_id, user_id)
    await call.answer("✅ Вы участвуете в розыгрыше! Удачи!", show_alert=True)

# ========== АДМИН: ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ ==========
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
    
    # Проверяем подписку на обязательный канал
    is_subbed = await check_subscription(user[0])
    
    text = (
        f"🔍 *Информация о пользователе*\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"📝 Username: @{user[1] or 'нет'}\n"
        f"⭐ Баланс: {user[2]} Stars\n"
        f"🚫 Статус: {'Заблокирован' if user[3] else 'Активен'}\n"
        f"👥 Рефералов: {user[4]}\n"
        f"📋 Выполнено заданий: {user[6]}\n\n"
        f"📢 *Обязательный канал:*\n"
        f"{'✅ Подписан' if is_subbed else '❌ НЕ ПОДПИСАН'}"
    )
    
    await msg.answer(text, parse_mode="Markdown")
    await state.clear()

# ========== АДМИН: СОЗДАНИЕ РОЗЫГРЫША ==========
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
    
    giveaway_id = add_giveaway(data['title'], data['prize'], data['end_date'], channels)
    
    # Публикация в канале
    text = (
        f"🎉 *НОВЫЙ РОЗЫГРЫШ!* 🎉\n\n"
        f"📌 *{data['title']}*\n"
        f"🏆 Приз: {data['prize']}\n"
        f"⏰ Заканчивается: {data['end_date']}\n\n"
        f"👉 Участвовать в боте: @{config.REQUIRED_CHANNEL}\n"
    )
    
    if channels and channels != "0":
        text += f"\n📢 *Обязательная подписка:*\n"
        for ch in channels.split(','):
            if ch.strip():
                text += f"• @{ch.strip()}\n"
    
    try:
        await bot.send_message(f"@{config.REQUIRED_CHANNEL}", text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки в канал: {e}")
    
    await msg.answer(f"✅ Розыгрыш «{data['title']}» создан!", reply_markup=admin_panel())
    await state.clear()

# ========== АДМИН: КАНАЛЫ ==========
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
        add_channel(data['channel_id'], data['name'], stars)
        await msg.answer(f"✅ Канал «{data['name']}» добавлен! Награда: {stars}⭐")
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число")

@dp.callback_query(F.data == "admin_list_channels")
async def list_channels(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    channels = get_all_channels()
    if not channels:
        await call.answer("Нет каналов", show_alert=True)
        return
    text = "📋 *Все каналы:*\n\n"
    for ch in channels:
        required = "🔒 ОБЯЗАТЕЛЬНЫЙ" if ch[4] else "📌 Обычный"
        text += f"• {ch[2]}: @{ch[1]} | {ch[3]}⭐ | {required}\n"
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())

@dp.callback_query(F.data == "admin_del_channel")
async def delete_channel_menu(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    channels = get_channels()
    if not channels:
        await call.answer("Нет каналов для удаления", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=f"❌ {ch[2]}", callback_data=f"delch_{ch[1]}")] for ch in channels]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    await call.message.edit_text("🗑 Выберите канал для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("delch_"))
async def confirm_delete_channel(call: types.CallbackQuery):
    channel_id = call.data.split("_")[1]
    delete_channel(channel_id)
    await call.answer("✅ Канал удалён", show_alert=True)
    await call.message.delete()

# ========== АДМИН: ВЫДАЧА ПО USERNAME ==========
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
        user_id = user[0] if user else None
    else:
        try:
            user_id = int(query)
            user = get_user(user_id)
        except:
            user = None
    
    if not user:
        await msg.answer("❌ Пользователь не найден!")
        await state.clear()
        return
    
    await state.update_data(target_user=user[0])
    await msg.answer(f"💰 Введите сумму для начисления @{user[1] or user[0]}:\nТекущий баланс: {user[2]}⭐")
    await state.set_state(AdminStates.waiting_balance_amount)

@dp.message(AdminStates.waiting_balance_amount)
async def give_balance_step3(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data['target_user']
        update_balance(user_id, amount)
        user = get_user(user_id)
        await msg.answer(f"✅ Начислено {amount}⭐ пользователю @{user[1] or user_id}\nНовый баланс: {user[2]}⭐")
        try:
            await bot.send_message(user_id, f"💰 Администратор начислил вам {amount}⭐!\nВаш баланс: {user[2]}⭐")
        except:
            pass
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число")

# ========== АДМИН: ЗАЯВКИ ==========
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
        await call.message.answer(f"📨 *Заявка #{req[0]}*\nОт: @{req[2]} ({req[1]})\nСумма: {req[3]}⭐", 
                                  parse_mode="Markdown", reply_markup=buttons)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdrawal(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_withdrawal_status(req_id, "approved")
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
        update_balance(req[0], req[1])
        update_withdrawal_status(req_id, "rejected")
        try:
            await bot.send_message(req[0], f"❌ Ваша заявка на вывод {req[1]}⭐ отклонена. Средства возвращены.")
        except:
            pass
        await call.answer("❌ Отклонено", show_alert=True)
        await call.message.delete()

# ========== АДМИН: БАН ==========
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
    
    if user[3] == 1:
        unban_user(user[0])
        await msg.answer(f"✅ Пользователь @{user[1] or user[0]} разблокирован")
    else:
        ban_user(user[0])
        await msg.answer(f"✅ Пользователь @{user[1] or user[0]} заблокирован")
    await state.clear()

# ========== АДМИН: РАССЫЛКА ==========
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

# ========== НАЗАД ==========
@dp.callback_query(F.data == "admin_back")
async def back_to_admin(call: types.CallbackQuery):
    await call.message.edit_text("🛠 Админ-панель", reply_markup=admin_panel())

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text("✨ Главное меню", reply_markup=main_menu())

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("🤖 Бот запущен!")
    print(f"✅ Обязательный канал: @{config.REQUIRED_CHANNEL}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
