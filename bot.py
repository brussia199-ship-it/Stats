import asyncio
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

# Состояния FSM
class AdminStates(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_name = State()
    waiting_channel_stars = State()
    waiting_balance_user_id = State()
    waiting_balance_amount = State()
    waiting_ban_user_id = State()
    waiting_broadcast = State()
    waiting_withdraw_amount = State()

# Главное меню пользователя
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="💸 Вывод Stars", callback_data="withdraw")],
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="referral")]
    ])

# Админ-панель
def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="🗑 Удалить канал", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="📝 Список каналов", callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="💰 Выдать чек на баланс", callback_data="admin_give_balance")],
        [InlineKeyboardButton(text="🔨 Бан/Разбан", callback_data="admin_ban_menu")],
        [InlineKeyboardButton(text="✅ Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ])

@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    
    # Проверка на бан
    user = get_user(user_id)
    if user and user[2] == 1:
        await msg.answer("🚫 Вы заблокированы!")
        return
    
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if ref == user_id:
        ref = None
    
    add_user(user_id, ref)
    await msg.answer(
        "✨ Добро пожаловать! Зарабатывай Stars за подписки.\n"
        "📌 Как заработать:\n"
        "• Подпишись на каналы → +0.25⭐ за каждый\n"
        "• Приглашай друзей → +3⭐ после выполнения ими 3 заданий\n"
        "• Вывод от 15⭐",
        reply_markup=main_menu()
    )

@dp.message(Command("admin"))
async def admin(msg: types.Message):
    if msg.from_user.id == config.ADMIN_ID:
        await msg.answer("🛠 Админ-панель", reply_markup=admin_panel())

# ========== ЗАДАНИЯ ==========
@dp.callback_query(F.data == "tasks")
async def show_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    user = get_user(user_id)
    if user and user[2] == 1:
        await call.answer("Вы заблокированы!", show_alert=True)
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
    
    if is_completed(user_id, channel_id):
        await call.answer("❌ Ты уже получил Stars за этот канал!", show_alert=True)
        return
    
    mark_completed(user_id, channel_id)
    update_balance(user_id, stars)
    
    # Проверка реферальных бонусов (после 3 заданий)
    completed_count = get_user_completed_count(user_id)
    user = get_user(user_id)
    if completed_count == 3 and user and user[4]:  # ref_by существует
        update_balance(user[4], 3)
        await bot.send_message(user[4], f"🎉 Ваш друг выполнил 3 задания! Вы получили +3⭐")
    
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
        f"⭐ *Твой баланс:* {user[1]} Stars\n"
        f"👥 *Приглашено друзей:* {user[3]}\n"
        f"📋 *Выполнено заданий:* {user[5]}\n"
        f"💸 *Минимальный вывод:* 15 Stars",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== ВЫВОД ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    if not user or user[2] == 1:
        await call.answer("Доступ запрещён", show_alert=True)
        return
    
    if user[1] < 15:
        await call.answer("❌ Недостаточно Stars. Нужно минимум 15⭐", show_alert=True)
        return
    
    await call.message.edit_text("💸 *Введите сумму для вывода:*\n(Минимум 15⭐, максимум весь баланс)", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_withdraw_amount)

@dp.message(AdminStates.waiting_withdraw_amount)
async def process_withdraw(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        user_id = msg.from_user.id
        user = get_user(user_id)
        
        if amount < 15:
            await msg.answer("❌ Минимальная сумма вывода - 15⭐")
            return
        
        if user[1] < amount:
            await msg.answer(f"❌ Недостаточно Stars. Ваш баланс: {user[1]}⭐")
            return
        
        add_withdrawal(user_id, amount)
        update_balance(user_id, -amount)
        await msg.answer(f"✅ Заявка на вывод {amount}⭐ отправлена администратору!\nОжидайте обработки.", reply_markup=main_menu())
        await state.clear()
        
        # Уведомление админу
        await bot.send_message(config.ADMIN_ID, f"📨 Новая заявка на вывод!\nОт: {user_id}\nСумма: {amount}⭐")
        
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
        f"👥 *Приглашено:* {get_user(user_id)[3]} друзей",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ========== АДМИН: ДОБАВЛЕНИЕ КАНАЛА ==========
@dp.callback_query(F.data == "admin_add_channel")
async def add_channel_step1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Доступ запрещён", show_alert=True)
        return
    await call.message.answer("📎 Введите username канала (без @):\nПример: `durov`", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_channel_id)

@dp.message(AdminStates.waiting_channel_id)
async def add_channel_step2(msg: types.Message, state: FSMContext):
    await state.update_data(channel_id=msg.text.strip())
    await msg.answer("📝 Введите название канала (как оно отображается в TG):")
    await state.set_state(AdminStates.waiting_channel_name)

@dp.message(AdminStates.waiting_channel_name)
async def add_channel_step3(msg: types.Message, state: FSMContext):
    await state.update_data(channel_name=msg.text.strip())
    await msg.answer("⭐ Введите количество Stars за подписку (например: 0.25):")
    await state.set_state(AdminStates.waiting_channel_stars)

@dp.message(AdminStates.waiting_channel_stars)
async def add_channel_step4(msg: types.Message, state: FSMContext):
    try:
        stars = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        add_channel(data['channel_id'], data['channel_name'], stars)
        await msg.answer(f"✅ Канал «{data['channel_name']}» добавлен! Награда: {stars}⭐")
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число (например: 0.25)")

# ========== АДМИН: УДАЛЕНИЕ КАНАЛА ==========
@dp.callback_query(F.data == "admin_del_channel")
async def delete_channel_menu(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    channels = get_channels()
    if not channels:
        await call.answer("Нет каналов для удаления", show_alert=True)
        return
    
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=f"❌ {ch[2]}", callback_data=f"delch_{ch[1]}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    
    await call.message.edit_text("🗑 Выберите канал для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("delch_"))
async def confirm_delete_channel(call: types.CallbackQuery):
    channel_id = call.data.split("_")[1]
    delete_channel(channel_id)
    await call.answer("✅ Канал удалён", show_alert=True)
    await call.message.delete()

# ========== АДМИН: СПИСОК КАНАЛОВ ==========
@dp.callback_query(F.data == "admin_list_channels")
async def list_channels(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    
    channels = get_channels()
    if not channels:
        await call.answer("Нет каналов", show_alert=True)
        return
    
    text = "📋 *Список каналов:*\n\n"
    for ch in channels:
        text += f"• {ch[2]}: @{ch[1]} | {ch[3]}⭐\n"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())

# ========== АДМИН: ВЫДАЧА БАЛАНСА ==========
@dp.callback_query(F.data == "admin_give_balance")
async def give_balance_step1(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🆔 Введите user_id пользователя:")
    await state.set_state(AdminStates.waiting_balance_user_id)

@dp.message(AdminStates.waiting_balance_user_id)
async def give_balance_step2(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text)
        user = get_user(user_id)
        if not user:
            await msg.answer("❌ Пользователь не найден!")
            await state.clear()
            return
        await state.update_data(target_user=user_id)
        await msg.answer(f"💰 Введите сумму для начисления пользователю {user_id}:\nТекущий баланс: {user[1]}⭐")
        await state.set_state(AdminStates.waiting_balance_amount)
    except ValueError:
        await msg.answer("❌ Введите число (user_id)")

@dp.message(AdminStates.waiting_balance_amount)
async def give_balance_step3(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data['target_user']
        update_balance(user_id, amount)
        user = get_user(user_id)
        await msg.answer(f"✅ Начислено {amount}⭐ пользователю {user_id}\nНовый баланс: {user[1]}⭐")
        await bot.send_message(user_id, f"💰 Администратор начислил вам {amount}⭐!\nВаш баланс: {user[1]}⭐")
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число")

# ========== АДМИН: БАН/РАЗБАН ==========
@dp.callback_query(F.data == "admin_ban_menu")
async def ban_menu(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🔨 Введите user_id для блокировки/разблокировки:")
    await state.set_state(AdminStates.waiting_ban_user_id)

@dp.message(AdminStates.waiting_ban_user_id)
async def process_ban(msg: types.Message, state: FSMContext):
    try:
        user_id = int(msg.text)
        user = get_user(user_id)
        if not user:
            await msg.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        if user[2] == 1:
            unban_user(user_id)
            await msg.answer(f"✅ Пользователь {user_id} разблокирован")
            await bot.send_message(user_id, "🔓 Вы разблокированы администратором!")
        else:
            ban_user(user_id)
            await msg.answer(f"✅ Пользователь {user_id} заблокирован")
            await bot.send_message(user_id, "🔒 Вы заблокированы администратором!")
        await state.clear()
    except ValueError:
        await msg.answer("❌ Введите число (user_id)")

# ========== АДМИН: ЗАЯВКИ НА ВЫВОД ==========
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
        await call.message.answer(f"📨 *Заявка #{req[0]}*\nОт: `{req[1]}`\nСумма: {req[2]}⭐", 
                                  parse_mode="Markdown", reply_markup=buttons)
    
    if requests:
        await call.answer(f"Найдено {len(requests)} заявок")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdrawal(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    req = cursor.fetchone()
    if req:
        update_withdrawal_status(req_id, "approved")
        await bot.send_message(req[0], f"✅ Ваша заявка на вывод {req[1]}⭐ одобрена!\nСледите за поступлением Stars.")
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
        await bot.send_message(req[0], f"❌ Ваша заявка на вывод {req[1]}⭐ отклонена администратором.\nСредства возвращены на баланс.")
        await call.answer("❌ Отклонено", show_alert=True)
        await call.message.delete()

# ========== АДМИН: РАССЫЛКА ==========
@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("📢 Введите текст рассылки (можно с HTML-разметкой):")
    await state.set_state(AdminStates.waiting_broadcast)

@dp.message(AdminStates.waiting_broadcast)
async def send_broadcast(msg: types.Message, state: FSMContext):
    text = msg.text
    users = get_all_users()
    success = 0
    fail = 0
    
    status_msg = await msg.answer("📤 Идёт рассылка...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\n📨 Доставлено: {success}\n❌ Ошибок: {fail}")
    await state.clear()

# ========== НАЗАД В АДМИН-ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_back")
async def back_to_admin(call: types.CallbackQuery):
    await call.message.edit_text("🛠 Админ-панель", reply_markup=admin_panel())

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("🤖 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
