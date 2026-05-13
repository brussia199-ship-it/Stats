import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database import *
import os

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Путь к картинке для оформления (положите файл image.jpg в папку с ботом)
IMAGE_PATH = "image.jpg"

async def send_with_image(chat_id, text, reply_markup=None):
    """Отправляет сообщение с картинкой"""
    if os.path.exists(IMAGE_PATH):
        photo = FSInputFile(IMAGE_PATH)
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)

async def edit_with_image(message, text, reply_markup=None):
    """Редактирует сообщение с картинкой"""
    if os.path.exists(IMAGE_PATH):
        photo = FSInputFile(IMAGE_PATH)
        await message.delete()
        await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await message.edit_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)

class AdminStates(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_name = State()
    waiting_channel_stars = State()
    waiting_balance_user = State()
    waiting_balance_amount = State()
    waiting_ban_user = State()
    waiting_broadcast = State()
    waiting_withdraw_amount = State()
    waiting_check_user = State()
    waiting_add_admin_id = State()
    waiting_remove_admin_id = State()
    waiting_promocode_code = State()
    waiting_promocode_reward = State()
    waiting_promocode_uses = State()
    waiting_promocode_expiry = State()
    waiting_donate_amount = State()
    waiting_user_promocode = State()

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{config.REQUIRED_CHANNEL}", user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="♦ Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="♦ Вывод Stars", callback_data="withdraw")],
        [InlineKeyboardButton(text="♦ Пригласить друга", callback_data="referral")],
        [InlineKeyboardButton(text="♦ Ежедневный бонус", callback_data="daily")],
        [InlineKeyboardButton(text="♦ Ежечасный бонус", callback_data="hourly")],
        [InlineKeyboardButton(text="♦ Промокод", callback_data="enter_promocode")],
        [InlineKeyboardButton(text="♦ Донат", callback_data="donate")]
    ])

def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Добавить канал", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="♦ Удалить канал", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="♦ Список каналов", callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="♦ Выдать чек", callback_data="admin_give_balance")],
        [InlineKeyboardButton(text="♦ Бан/Разбан", callback_data="admin_ban_menu")],
        [InlineKeyboardButton(text="♦ Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="♦ Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="♦ Управление админами", callback_data="admin_manage_admins")],
        [InlineKeyboardButton(text="♦ Промокоды", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="♦ Донаты", callback_data="admin_donations")],
        [InlineKeyboardButton(text="♦ Проверить пользователя", callback_data="admin_check_user")]
    ])

def promocodes_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Создать", callback_data="admin_create_promocode")],
        [InlineKeyboardButton(text="♦ Список", callback_data="admin_list_promocodes")],
        [InlineKeyboardButton(text="♦ Удалить", callback_data="admin_delete_promocode")],
        [InlineKeyboardButton(text="♦ Назад", callback_data="admin_back")]
    ])

def donations_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Все донаты", callback_data="admin_list_donations")],
        [InlineKeyboardButton(text="♦ Ожидающие", callback_data="admin_pending_donations")],
        [InlineKeyboardButton(text="♦ Назад", callback_data="admin_back")]
    ])

@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or str(user_id)
    first_name = msg.from_user.first_name
    last_name = msg.from_user.last_name
    
    user = get_user(user_id)
    if user and user['is_banned'] == 1:
        await msg.answer("♦ Вы заблокированы!")
        return
    
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if ref == user_id:
        ref = None
    
    add_user(user_id, username, first_name, last_name, ref)
    
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="♦ ПОДПИСАТЬСЯ", url=f"https://t.me/{config.REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="♦ ПРОВЕРИТЬ", callback_data="check_sub")]
        ])
        await msg.answer(
            f"♦ *Для использования бота подпишитесь на канал!*\n\n"
            f"♦ [{config.REQUIRED_CHANNEL}](https://t.me/{config.REQUIRED_CHANNEL})",
            parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True
        )
        return
    
    await send_with_image(
        msg.chat.id,
        "♦ *Добро пожаловать!* ♦\n\n"
        "♦ *Как заработать Stars:*\n"
        "• ♦ Подписка на каналы → +0.25♦\n"
        "• ♦ Приглашение друзей → +3♦\n"
        "• ♦ Ежедневный бонус → +1♦\n"
        "• ♦ Ежечасный бонус → +0.25♦\n\n"
        "♦ *Вывод от 15♦*",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "check_sub")
async def check_subscription_handler(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await edit_with_image(call.message, "♦ Спасибо за подписку!", reply_markup=main_menu())
    else:
        await call.answer("♦ Вы не подписаны!", show_alert=True)

@dp.message(Command("admin"))
async def admin(msg: types.Message):
    user_id = msg.from_user.id
    if is_admin(user_id) or user_id == 7673683792:
        await send_with_image(msg.chat.id, "♦ *Админ-панель*", reply_markup=admin_panel())
    else:
        await msg.answer("♦ Нет доступа!")

@dp.callback_query(F.data == "tasks")
async def show_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    channels = get_channels()
    if not channels:
        await edit_with_image(call.message, "♦ Заданий нет.", reply_markup=main_menu())
        return
    
    text = "♦ *Подпишись и нажми Готово:*\n\n"
    buttons = []
    
    for ch in channels:
        channel_id, name, stars = ch
        if is_completed(user_id, channel_id):
            text += f"▪ {name} - выполнено (+{stars}♦)\n"
        else:
            text += f"▪ {name} (+{stars}♦)\n"
            buttons.append([InlineKeyboardButton(text=f"▪ Подписаться", url=f"https://t.me/{channel_id}")])
            buttons.append([InlineKeyboardButton(text=f"▪ Готово (+{stars}♦)", callback_data=f"complete_{channel_id}_{stars}")])
    
    if buttons:
        await edit_with_image(call.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await edit_with_image(call.message, "♦ Все задания выполнены!", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("complete_"))
async def complete_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    parts = call.data.split("_")
    channel_id = parts[1]
    stars = float(parts[2])
    
    if not await check_subscription(user_id):
        await call.answer("♦ Отписка от канала!", show_alert=True)
        return
    
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel_id}", user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await call.answer("♦ Вы не подписаны!", show_alert=True)
            return
    except:
        await call.answer("♦ Ошибка проверки", show_alert=True)
        return
    
    if is_completed(user_id, channel_id):
        await call.answer("♦ Уже получено!", show_alert=True)
        return
    
    mark_completed(user_id, channel_id, stars)
    update_balance(user_id, stars, f"Подписка на {channel_id}")
    
    completed_count = get_completed_count(user_id)
    user = get_user(user_id)
    if completed_count == 3 and user and user['ref_by']:
        update_balance(user['ref_by'], 3, f"Реферальный бонус")
        try:
            await bot.send_message(user['ref_by'], f"♦ Ваш друг выполнил 3 задания! +3♦")
        except:
            pass
    
    await call.answer(f"+{stars}♦", show_alert=True)
    await edit_with_image(call.message, "♦ Готово!", reply_markup=main_menu())

@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.answer("Ошибка", show_alert=True)
        return
    
    await edit_with_image(
        call.message,
        f"♦ *Баланс:* {user['balance']} Stars\n"
        f"♦ *Рефералов:* {user['referrals']}\n"
        f"♦ *Заданий:* {user['tasks_completed']}\n"
        f"♦ *Заработано:* {user['total_earned']} Stars\n"
        f"♦ *Выведено:* {user['total_withdrawn']} Stars\n"
        f"♦ *Мин. вывод:* 15 Stars",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "withdraw")
async def withdraw_start(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    if not user or user['is_banned'] == 1:
        await call.answer("Доступ запрещён", show_alert=True)
        return
    
    if not await check_subscription(call.from_user.id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    if user['balance'] < 15:
        await call.answer("♦ Нужно минимум 15♦", show_alert=True)
        return
    
    await edit_with_image(call.message, "♦ *Введите сумму вывода:*\n(мин. 15♦, макс. весь баланс)")
    await state.set_state(AdminStates.waiting_withdraw_amount)

@dp.message(AdminStates.waiting_withdraw_amount)
async def process_withdraw(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        user_id = msg.from_user.id
        username = msg.from_user.username or str(user_id)
        user = get_user(user_id)
        
        if amount < 15:
            await msg.answer("♦ Минимум 15♦")
            return
        
        if user['balance'] < amount:
            await msg.answer(f"♦ Не хватает. Баланс: {user['balance']}♦")
            return
        
        add_withdrawal(user_id, username, amount)
        update_balance(user_id, -amount, f"Заявка на вывод {amount}♦")
        await msg.answer(f"♦ Заявка на {amount}♦ отправлена!", reply_markup=main_menu())
        await state.clear()
        
        admins = get_all_admins()
        for admin in admins:
            try:
                await bot.send_message(admin[0], f"♦ *Заявка на вывод!*\nОт: @{username}\nСумма: {amount}♦", parse_mode="Markdown")
            except:
                pass
    except ValueError:
        await msg.answer("♦ Введите число!")

@dp.callback_query(F.data == "referral")
async def referral(call: types.CallbackQuery):
    user_id = call.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    user = get_user(user_id)
    
    await edit_with_image(
        call.message,
        f"♦ *Реферальная программа*\n\n"
        f"♦ Ссылка:\n`{link}`\n\n"
        f"♦ *Условия:*\n"
        f"• Друг переходит по ссылке\n"
        f"• Выполняет 3 задания\n"
        f"• Вы получаете +3♦\n\n"
        f"♦ Приглашено: {user['referrals'] if user else 0}",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "daily")
async def daily_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    if can_claim_daily(user_id):
        update_balance(user_id, 1.0, "Ежедневный бонус")
        set_daily_claimed(user_id)
        await call.answer("♦ +1♦", show_alert=True)
        await edit_with_image(call.message, "♦ Бонус получен! Ждите завтра.", reply_markup=main_menu())
    else:
        await call.answer("♦ Уже получен сегодня!", show_alert=True)

@dp.callback_query(F.data == "hourly")
async def hourly_bonus(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    if can_claim_hourly(user_id):
        update_balance(user_id, 0.25, "Ежечасный бонус")
        set_hourly_claimed(user_id)
        await call.answer("♦ +0.25♦", show_alert=True)
        await edit_with_image(call.message, "♦ Бонус получен! Ждите час.", reply_markup=main_menu())
    else:
        await call.answer("♦ Уже получен!", show_alert=True)

# ========== ПРОМОКОДЫ (РАБОТАЮТ!) ==========
@dp.callback_query(F.data == "enter_promocode")
async def enter_promocode_start(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    await edit_with_image(call.message, "♦ *Введите промокод:*\n\nПример: `SUMMER2024`")
    await state.set_state(AdminStates.waiting_user_promocode)

@dp.message(AdminStates.waiting_user_promocode)
async def process_promocode(msg: types.Message, state: FSMContext):
    code = msg.text.strip().upper()
    user_id = msg.from_user.id
    
    # Получаем промокод из БД
    cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code,))
    promo = cursor.fetchone()
    
    if not promo:
        await msg.answer(f"♦ Промокод `{code}` не найден!", reply_markup=main_menu())
        await state.clear()
        return
    
    # Проверяем активность
    if promo[8] != 1:
        await msg.answer(f"♦ Промокод `{code}` неактивен!", reply_markup=main_menu())
        await state.clear()
        return
    
    # Проверяем остаток использований
    if promo[3] <= 0:
        await msg.answer(f"♦ Промокод `{code}` использован максимальное число раз!", reply_markup=main_menu())
        await state.clear()
        return
    
    # Проверяем срок действия
    if promo[7]:
        expires = datetime.fromisoformat(promo[7])
        if expires < datetime.now():
            cursor.execute('UPDATE promocodes SET is_active = 0 WHERE code = ?', (code,))
            conn.commit()
            await msg.answer(f"♦ Срок действия промокода `{code}` истёк!", reply_markup=main_menu())
            await state.clear()
            return
    
    # Проверяем, использовал ли пользователь
    cursor.execute('SELECT 1 FROM promocode_uses WHERE code = ? AND user_id = ?', (code, user_id))
    if cursor.fetchone():
        await msg.answer(f"♦ Вы уже использовали промокод `{code}`!", reply_markup=main_menu())
        await state.clear()
        return
    
    # Начисляем награду
    reward = promo[2]
    update_balance(user_id, reward, f"Промокод: {code}")
    
    # Обновляем счетчик
    uses_left = promo[3] - 1
    cursor.execute('UPDATE promocodes SET uses_left = ? WHERE code = ?', (uses_left, code))
    cursor.execute('INSERT INTO promocode_uses (code, user_id, used_at) VALUES (?, ?, ?)', (code, user_id, datetime.now()))
    
    if uses_left == 0:
        cursor.execute('UPDATE promocodes SET is_active = 0 WHERE code = ?', (code,))
    
    conn.commit()
    
    user = get_user(user_id)
    await msg.answer(
        f"♦ *Промокод активирован!*\n\n"
        f"💰 Вы получили {reward}♦\n"
        f"♦ Новый баланс: {user['balance']} Stars",
        parse_mode="Markdown", reply_markup=main_menu()
    )
    await state.clear()

# ========== ДОНАТЫ ЧЕРЕЗ TELEGRAM STARS ==========
@dp.callback_query(F.data == "donate")
async def donate_start(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if not await check_subscription(user_id):
        await call.answer("♦ Подпишитесь на канал!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 ♦", callback_data="donate_10"),
         InlineKeyboardButton(text="25 ♦", callback_data="donate_25"),
         InlineKeyboardButton(text="50 ♦", callback_data="donate_50")],
        [InlineKeyboardButton(text="100 ♦", callback_data="donate_100"),
         InlineKeyboardButton(text="250 ♦", callback_data="donate_250"),
         InlineKeyboardButton(text="500 ♦", callback_data="donate_500")],
        [InlineKeyboardButton(text="♦ Другая сумма", callback_data="donate_custom")],
        [InlineKeyboardButton(text="♦ Назад", callback_data="back_to_menu")]
    ])
    
    await edit_with_image(
        call.message,
        "♦ *Поддержать проект* ♦\n\n"
        "Выберите сумму доната в Telegram Stars.\n"
        "Средства пойдут на развитие бота!\n\n"
        "♦ 1 Star = поддержка проекта",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("donate_"))
async def process_donate(call: types.CallbackQuery, state: FSMContext):
    amount_str = call.data.split("_")[1]
    
    if amount_str == "custom":
        await edit_with_image(call.message, "♦ *Введите сумму доната:*\n(от 1 до 1000 ♦)")
        await state.set_state(AdminStates.waiting_donate_amount)
        return
    
    amount = int(amount_str)
    await send_invoice(call, amount)

@dp.message(AdminStates.waiting_donate_amount)
async def process_custom_donate(msg: types.Message, state: FSMContext):
    try:
        amount = int(msg.text)
        
        if amount < 1:
            await msg.answer("♦ Минимум 1 ♦")
            return
        if amount > 1000:
            await msg.answer("♦ Максимум 1000 ♦")
            return
        
        class FakeCall:
            from_user = msg.from_user
            message = msg
        
        await send_invoice(FakeCall(), amount)
        await state.clear()
        
    except ValueError:
        await msg.answer("♦ Введите число!")

async def send_invoice(call, amount):
    user_id = call.from_user.id
    username = call.from_user.username or str(user_id)
    
    donation_id = create_donation(user_id, username, float(amount))
    
    title = "Поддержка проекта"
    description = f"Спасибо за донат! Вы получите +{amount}♦ на баланс."
    payload = f"donation_{donation_id}"
    currency = "XTR"
    prices = [LabeledPrice(label="Донат", amount=amount)]
    
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=currency,
        prices=prices,
        start_parameter="donation"
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    amount = message.successful_payment.total_amount
    payload = message.successful_payment.invoice_payload
    
    donation_id = int(payload.split("_")[1])
    
    update_donation_status(donation_id, 'paid')
    update_balance(user_id, float(amount), f"Донат {amount}♦")
    
    user = get_user(user_id)
    await message.answer(
        f"♦ *Спасибо за донат!*\n\n"
        f"💰 Начислено: +{amount}♦\n"
        f"♦ Ваш баланс: {user['balance']} Stars\n\n"
        f"Спасибо, что помогаете проекту!",
        parse_mode="Markdown", reply_markup=main_menu()
    )
    
    admins = get_all_admins()
    for admin in admins:
        try:
            await bot.send_message(
                admin[0],
                f"♦ *Новый донат!*\n"
                f"От: @{message.from_user.username or user_id}\n"
                f"Сумма: {amount}♦",
                parse_mode="Markdown"
            )
        except:
            pass

# ========== АДМИН: УПРАВЛЕНИЕ ПРОМОКОДАМИ ==========
@dp.callback_query(F.data == "admin_promocodes")
async def admin_promocodes_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await edit_with_image(call.message, "♦ *Управление промокодами*", reply_markup=promocodes_menu())

@dp.callback_query(F.data == "admin_create_promocode")
async def create_promocode_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите код промокода (буквы и цифры):")
    await state.set_state(AdminStates.waiting_promocode_code)

@dp.message(AdminStates.waiting_promocode_code)
async def create_promocode_code(msg: types.Message, state: FSMContext):
    code = msg.text.strip().upper()
    if not code.isalnum():
        await msg.answer("♦ Только буквы и цифры!")
        return
    
    cursor.execute('SELECT * FROM promocodes WHERE code = ?', (code,))
    existing = cursor.fetchone()
    if existing:
        await msg.answer("♦ Такой код уже существует!")
        return
    
    await state.update_data(code=code)
    await msg.answer("♦ Введите награду в Stars:")
    await state.set_state(AdminStates.waiting_promocode_reward)

@dp.message(AdminStates.waiting_promocode_reward)
async def create_promocode_reward(msg: types.Message, state: FSMContext):
    try:
        reward = float(msg.text)
        if reward <= 0:
            await msg.answer("♦ Награда > 0!")
            return
        await state.update_data(reward=reward)
        await msg.answer("♦ Введите количество использований:")
        await state.set_state(AdminStates.waiting_promocode_uses)
    except:
        await msg.answer("♦ Введите число!")

@dp.message(AdminStates.waiting_promocode_uses)
async def create_promocode_uses(msg: types.Message, state: FSMContext):
    try:
        max_uses = int(msg.text)
        if max_uses <= 0:
            await msg.answer("♦ > 0!")
            return
        await state.update_data(max_uses=max_uses)
        await msg.answer("♦ Введите срок (часы) или 0 для бессрочного:")
        await state.set_state(AdminStates.waiting_promocode_expiry)
    except:
        await msg.answer("♦ Введите число!")

@dp.message(AdminStates.waiting_promocode_expiry)
async def create_promocode_expiry(msg: types.Message, state: FSMContext):
    try:
        hours = int(msg.text)
        data = await state.get_data()
        
        expires_at = None
        if hours > 0:
            expires_at = (datetime.now() + timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            INSERT INTO promocodes (code, reward, uses_left, max_uses, created_by, expires_at, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        ''', (data['code'], data['reward'], data['max_uses'], data['max_uses'], msg.from_user.id, expires_at, datetime.now()))
        conn.commit()
        
        await msg.answer(
            f"♦ *Промокод создан!*\n"
            f"♦ Код: `{data['code']}`\n"
            f"♦ Награда: {data['reward']}♦\n"
            f"♦ Лимит: {data['max_uses']}\n"
            f"♦ Срок: {'бессрочно' if hours == 0 else f'{hours}ч'}",
            parse_mode="Markdown", reply_markup=promocodes_menu()
        )
        await state.clear()
    except:
        await msg.answer("♦ Введите число!")

@dp.callback_query(F.data == "admin_list_promocodes")
async def list_promocodes_admin(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    
    cursor.execute('SELECT * FROM promocodes ORDER BY created_at DESC')
    promos = cursor.fetchall()
    
    if not promos:
        await call.answer("Нет промокодов", show_alert=True)
        return
    
    text = "♦ *Список промокодов:*\n\n"
    for p in promos:
        used = p[4] - p[3]
        status = "▪" if p[8] else "◽"
        expires = "бессрочно" if not p[7] else p[7][:16]
        text += f"{status} `{p[1]}` | {p[2]}♦ | {used}/{p[4]} | до {expires}\n"
    
    await edit_with_image(call.message, text, reply_markup=promocodes_menu())

@dp.callback_query(F.data == "admin_delete_promocode")
async def delete_promocode_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите код промокода для удаления:")
    await state.set_state(AdminStates.waiting_promocode_code)

@dp.message(AdminStates.waiting_promocode_code)
async def delete_promocode_process(msg: types.Message, state: FSMContext):
    code = msg.text.strip().upper()
    
    cursor.execute('DELETE FROM promocodes WHERE code = ?', (code,))
    cursor.execute('DELETE FROM promocode_uses WHERE code = ?', (code,))
    conn.commit()
    
    if cursor.rowcount > 0:
        await msg.answer(f"♦ Промокод `{code}` удалён!", parse_mode="Markdown", reply_markup=promocodes_menu())
    else:
        await msg.answer(f"♦ Промокод `{code}` не найден!", parse_mode="Markdown")
    
    await state.clear()

# ========== АДМИН: ПРОСМОТР ДОНАТОВ ==========
@dp.callback_query(F.data == "admin_donations")
async def admin_donations_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await edit_with_image(call.message, "♦ *Управление донатами*", reply_markup=donations_menu())

@dp.callback_query(F.data == "admin_list_donations")
async def list_all_donations(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    
    cursor.execute('SELECT * FROM donations ORDER BY created_at DESC')
    donations = cursor.fetchall()
    
    if not donations:
        await call.answer("Нет донатов", show_alert=True)
        return
    
    text = "♦ *Все донаты:*\n\n"
    total = 0
    for don in donations:
        total += don[3]
        status = "▪" if don[4] == 'paid' else "◽"
        text += f"{status} @{don[2]} | {don[3]}♦ | {don[5][:10]}\n"
    
    text += f"\n♦ *Всего собрано: {total}♦*"
    await edit_with_image(call.message, text, reply_markup=donations_menu())

@dp.callback_query(F.data == "admin_pending_donations")
async def list_pending_donations(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    
    cursor.execute('SELECT * FROM donations WHERE status = "pending" ORDER BY created_at DESC')
    donations = cursor.fetchall()
    
    if not donations:
        await call.answer("Нет ожидающих донатов", show_alert=True)
        return
    
    text = "♦ *Ожидающие донаты:*\n\n"
    for don in donations:
        text += f"▪ #{don[0]} | @{don[2]} | {don[3]}♦\n"
    
    await edit_with_image(call.message, text, reply_markup=donations_menu())

# ========== АДМИН: ОСТАЛЬНЫЕ ФУНКЦИИ ==========
@dp.callback_query(F.data == "admin_add_channel")
async def add_channel_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите username канала (без @):")
    await state.set_state(AdminStates.waiting_channel_id)

@dp.message(AdminStates.waiting_channel_id)
async def add_channel_id(msg: types.Message, state: FSMContext):
    await state.update_data(channel_id=msg.text.strip())
    await msg.answer("♦ Введите название канала:")
    await state.set_state(AdminStates.waiting_channel_name)

@dp.message(AdminStates.waiting_channel_name)
async def add_channel_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await msg.answer("♦ Введите Stars за подписку (0.25):")
    await state.set_state(AdminStates.waiting_channel_stars)

@dp.message(AdminStates.waiting_channel_stars)
async def add_channel_stars(msg: types.Message, state: FSMContext):
    try:
        stars = float(msg.text)
        data = await state.get_data()
        add_channel(data['channel_id'], data['name'], stars, msg.from_user.id)
        await msg.answer(f"♦ Канал «{data['name']}» добавлен! Награда: {stars}♦")
        await state.clear()
    except:
        await msg.answer("♦ Введите число!")

@dp.callback_query(F.data == "admin_list_channels")
async def list_channels_admin(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    channels = get_all_channels()
    text = "♦ *Все каналы:*\n\n"
    for ch in channels:
        required = "▪ ОБЯЗАТЕЛЬНЫЙ" if ch[4] else "▪ Обычный"
        text += f"• {ch[2]}: @{ch[1]} | {ch[3]}♦ | {required}\n"
    await edit_with_image(call.message, text, reply_markup=admin_panel())

@dp.callback_query(F.data == "admin_del_channel")
async def delete_channel_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    channels = get_channels()
    if not channels:
        await call.answer("Нет каналов для удаления", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=f"▪ {ch[1]}", callback_data=f"delch_{ch[0]}")] for ch in channels]
    buttons.append([InlineKeyboardButton(text="♦ Назад", callback_data="admin_back")])
    await edit_with_image(call.message, "♦ Выберите канал:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("delch_"))
async def confirm_delete_channel(call: types.CallbackQuery):
    channel_id = call.data.split("_")[1]
    delete_channel(channel_id)
    await call.answer("♦ Канал удалён", show_alert=True)
    await call.message.delete()

@dp.callback_query(F.data == "admin_give_balance")
async def give_balance_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите @username или ID:")
    await state.set_state(AdminStates.waiting_balance_user)

@dp.message(AdminStates.waiting_balance_user)
async def give_balance_user(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    if query.startswith('@'):
        user = get_user_by_username(query[1:])
    else:
        try:
            user = get_user(int(query))
        except:
            user = None
    
    if not user:
        await msg.answer("♦ Пользователь не найден!")
        await state.clear()
        return
    
    await state.update_data(target_user=user['user_id'])
    await msg.answer(f"♦ Сумма для @{user['username'] or user['user_id']}:\nБаланс: {user['balance']}♦")
    await state.set_state(AdminStates.waiting_balance_amount)

@dp.message(AdminStates.waiting_balance_amount)
async def give_balance_amount(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text)
        data = await state.get_data()
        user_id = data['target_user']
        update_balance(user_id, amount, "Начислено админом")
        user = get_user(user_id)
        await msg.answer(f"♦ Начислено {amount}♦ @{user['username'] or user_id}\nНовый баланс: {user['balance']}♦")
        try:
            await bot.send_message(user_id, f"♦ Админ начислил {amount}♦!\nБаланс: {user['balance']}♦")
        except:
            pass
        await state.clear()
    except:
        await msg.answer("♦ Введите число!")

@dp.callback_query(F.data == "admin_withdrawals")
async def show_withdrawals_admin(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    reqs = get_pending_withdrawals()
    if not reqs:
        await call.answer("Нет заявок", show_alert=True)
        return
    
    for req in reqs:
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▪ Выплачено", callback_data=f"approve_{req[0]}"),
             InlineKeyboardButton(text="▪ Отклонить", callback_data=f"reject_{req[0]}")]
        ])
        await call.message.answer(f"♦ *Заявка #{req[0]}*\nОт: @{req[2]}\nСумма: {req[3]}♦\nДата: {req[5][:16]}", 
                                  parse_mode="Markdown", reply_markup=buttons)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdrawal_admin(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_withdrawal_status(req_id, "approved", call.from_user.id)
        try:
            await bot.send_message(req[0], f"♦ Заявка на вывод {req[1]}♦ одобрена!")
        except:
            pass
        await call.answer("♦ Выплачено", show_alert=True)
        await call.message.delete()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_withdrawal_admin(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_balance(req[0], req[1], "Возврат")
        update_withdrawal_status(req_id, "rejected", call.from_user.id)
        try:
            await bot.send_message(req[0], f"♦ Заявка на вывод {req[1]}♦ отклонена. Средства возвращены.")
        except:
            pass
        await call.answer("♦ Отклонено", show_alert=True)
        await call.message.delete()

@dp.callback_query(F.data == "admin_ban_menu")
async def ban_menu_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите @username или ID:")
    await state.set_state(AdminStates.waiting_ban_user)

@dp.message(AdminStates.waiting_ban_user)
async def ban_process(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    if query.startswith('@'):
        user = get_user_by_username(query[1:])
    else:
        try:
            user = get_user(int(query))
        except:
            user = None
    
    if not user:
        await msg.answer("♦ Пользователь не найден")
        await state.clear()
        return
    
    if user['is_banned'] == 1:
        unban_user(user['user_id'])
        await msg.answer(f"♦ @{user['username'] or user['user_id']} разблокирован")
    else:
        ban_user(user['user_id'])
        await msg.answer(f"♦ @{user['username'] or user['user_id']} заблокирован")
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите текст рассылки:")
    await state.set_state(AdminStates.waiting_broadcast)

@dp.message(AdminStates.waiting_broadcast)
async def send_broadcast(msg: types.Message, state: FSMContext):
    text = msg.text
    users = get_all_users()
    success = 0
    fail = 0
    
    status_msg = await msg.answer("♦ Рассылка...")
    
    for user_id, username in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    
    await status_msg.edit_text(f"♦ Рассылка завершена!\n▪ Доставлено: {success}\n▪ Ошибок: {fail}")
    await state.clear()

@dp.callback_query(F.data == "admin_check_user")
async def check_user_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите @username или ID:")
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
        await msg.answer("♦ Пользователь не найден")
        await state.clear()
        return
    
    is_subbed = await check_subscription(user['user_id'])
    
    text = (
        f"♦ *Информация*\n\n"
        f"▪ ID: `{user['user_id']}`\n"
        f"▪ Username: @{user['username'] or 'нет'}\n"
        f"▪ Баланс: {user['balance']} Stars\n"
        f"▪ Статус: {'Заблокирован' if user['is_banned'] else 'Активен'}\n"
        f"▪ Админ: {'Да' if is_admin(user['user_id']) else 'Нет'}\n"
        f"▪ Рефералов: {user['referrals']}\n"
        f"▪ Заданий: {user['tasks_completed']}\n"
        f"▪ Заработано: {user['total_earned']} Stars\n"
        f"▪ Канал: {'▪' if is_subbed else '◽'}"
    )
    
    await msg.answer(text, parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_manage_admins")
async def manage_admins(call: types.CallbackQuery):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    admins = get_all_admins()
    text = "♦ *Администраторы:*\n\n"
    for a in admins:
        text += f"▪ @{a[1] or a[0]} (ID: {a[0]})\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♦ Добавить", callback_data="admin_add_admin")],
        [InlineKeyboardButton(text="♦ Удалить", callback_data="admin_remove_admin")],
        [InlineKeyboardButton(text="♦ Назад", callback_data="admin_back")]
    ])
    await edit_with_image(call.message, text, reply_markup=keyboard)

@dp.callback_query(F.data == "admin_add_admin")
async def add_admin_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите ID пользователя:")
    await state.set_state(AdminStates.waiting_add_admin_id)

@dp.message(AdminStates.waiting_add_admin_id)
async def add_admin_process(msg: types.Message, state: FSMContext):
    try:
        new_id = int(msg.text.strip())
        user = get_user(new_id)
        if not user:
            await msg.answer("♦ Пользователь не найден!")
            await state.clear()
            return
        
        if add_admin(new_id, msg.from_user.id):
            await msg.answer(f"♦ @{user['username'] or new_id} теперь админ!")
        else:
            await msg.answer("♦ Уже админ!")
        await state.clear()
    except:
        await msg.answer("♦ Введите ID!")

@dp.callback_query(F.data == "admin_remove_admin")
async def remove_admin_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id) and call.from_user.id != 7673683792:
        return
    await call.message.answer("♦ Введите ID администратора:")
    await state.set_state(AdminStates.waiting_remove_admin_id)

@dp.message(AdminStates.waiting_remove_admin_id)
async def remove_admin_process(msg: types.Message, state: FSMContext):
    try:
        remove_id = int(msg.text.strip())
        
        if remove_id == 7673683792:
            await msg.answer("♦ Нельзя удалить главного админа!")
            await state.clear()
            return
        
        if remove_id == msg.from_user.id:
            await msg.answer("♦ Нельзя удалить себя!")
            await state.clear()
            return
        
        user = get_user(remove_id)
        if remove_admin(remove_id):
            await msg.answer(f"♦ @{user['username'] or remove_id} больше не админ!")
        else:
            await msg.answer("♦ Не является админом!")
        await state.clear()
    except:
        await msg.answer("♦ Введите ID!")

@dp.callback_query(F.data == "admin_back")
async def back_to_admin_panel(call: types.CallbackQuery):
    await edit_with_image(call.message, "♦ *Админ-панель*", reply_markup=admin_panel())

@dp.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(call: types.CallbackQuery):
    await edit_with_image(call.message, "♦ *Главное меню*", reply_markup=main_menu())

async def main():
    init_db()
    print("Бот запущен!")
    print(f"Канал: @{config.REQUIRED_CHANNEL}")
    print(f"Админ: 7673683792")
    if os.path.exists(IMAGE_PATH):
        print("Картинка для оформления загружена!")
    else:
        print("ВНИМАНИЕ: Картинка image.jpg не найдена! Положите её в папку с ботом.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
