import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config
from database import *

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Состояния FSM
class AdminStates(StatesGroup):
    waiting_channel_link = State()
    waiting_channel_name = State()
    waiting_balance_user_id = State()
    waiting_balance_amount = State()
    waiting_broadcast = State()
    waiting_withdraw_user_id = State()

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
        [InlineKeyboardButton(text="🔨 Бан/Разбан", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ])

@dp.message(Command("start"))
async def start(msg: types.Message):
    args = msg.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if ref == msg.from_user.id:
        ref = None
    add_user(msg.from_user.id, ref)
    await msg.answer("✨ Добро пожаловать! Зарабатывай Stars за подписки.", reply_markup=main_menu())

@dp.message(Command("admin"))
async def admin(msg: types.Message):
    if msg.from_user.id == config.ADMIN_ID:
        await msg.answer("🛠 Админ-панель", reply_markup=admin_panel())

# Задания
@dp.callback_query(F.data == "tasks")
async def show_tasks(call: types.CallbackQuery):
    user_id = call.from_user.id
    channels = get_channels()
    if not channels:
        await call.message.edit_text("❌ Заданий пока нет.")
        return
    text = "📢 Подпишись на каналы и нажми ✅ Готово:\n\n"
    buttons = []
    for ch in channels:
        ch_id, name = ch[1], ch[2]
        if is_completed(user_id, ch_id):
            text += f"✅ {name} - выполнено\n"
        else:
            text += f"📌 {name}\n"
            buttons.append([InlineKeyboardButton(text=f"Подписаться на {name}", url=f"https://t.me/{ch_id}")])
            buttons.append([InlineKeyboardButton(text=f"✅ Готово за {ch[3]}⭐", callback_data=f"complete_{ch_id}")])
    if buttons:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await call.message.edit_text("🎉 Ты выполнил все задания!")

@dp.callback_query(F.data.startswith("complete_"))
async def complete_task(call: types.CallbackQuery):
    user_id = call.from_user.id
    channel_id = call.data.split("_")[1]
    if is_completed(user_id, channel_id):
        await call.answer("Ты уже получил Stars за этот канал!", show_alert=True)
        return
    cursor.execute('SELECT stars FROM channels WHERE channel_id = ?', (channel_id,))
    row = cursor.fetchone()
    if not row:
        await call.answer("Ошибка", show_alert=True)
        return
    stars = row[0]
    update_balance(user_id, stars)
    mark_completed(user_id, channel_id)
    await call.answer(f"+{stars}⭐", show_alert=True)
    await call.message.edit_text("✅ Готово! Возвращайся в меню.", reply_markup=main_menu())

# Баланс и вывод
@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    await call.message.edit_text(f"⭐ Твой баланс: {user[1]} Stars\n💸 Минимальный вывод: 15 Stars", reply_markup=main_menu())

@dp.callback_query(F.data == "withdraw")
async def withdraw_menu(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user[1] < 15:
        await call.answer("❌ Недостаточно Stars. Нужно 15+", show_alert=True)
        return
    await call.message.edit_text("💸 Введи сумму для вывода (от 15):", reply_markup=main_menu())
    # Упрощённо: можно сделать через FSM, но для краткости - просто запрос

@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def process_withdraw(msg: types.Message):
    user_id = msg.from_user.id
    amount = float(msg.text)
    user = get_user(user_id)
    if user[1] < amount or amount < 15:
        await msg.answer("❌ Неверная сумма или недостаточно Stars.", reply_markup=main_menu())
        return
    add_withdrawal(user_id, amount)
    update_balance(user_id, -amount)
    await msg.answer(f"✅ Заявка на вывод {amount}⭐ отправлена админу.", reply_markup=main_menu())

# Реферальная система
@dp.callback_query(F.data == "referral")
async def referral(call: types.CallbackQuery):
    user_id = call.from_user.id
    link = f"https://t.me/{bot.username}?start={user_id}"
    await call.message.edit_text(f"👥 Приглашай друзей!\nЗа каждого друга, который выполнит 3 задания + капчу (упрощённо: просто задания), ты получишь 3⭐\n\nТвоя ссылка: {link}", reply_markup=main_menu())

# Админские обработчики (сокращённо, основные)
@dp.callback_query(F.data == "admin_add_channel")
async def add_channel_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("📎 Введите username канала (без @):")
    await state.set_state(AdminStates.waiting_channel_link)

@dp.message(AdminStates.waiting_channel_link)
async def add_channel_name(msg: types.Message, state: FSMContext):
    await state.update_data(channel_id=msg.text)
    await msg.answer("📝 Введите название канала:")
    await state.set_state(AdminStates.waiting_channel_name)

@dp.message(AdminStates.waiting_channel_name)
async def save_channel(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    add_channel(data['channel_id'], msg.text)
    await msg.answer("✅ Канал добавлен!")
    await state.clear()

@dp.callback_query(F.data == "admin_withdrawals")
async def list_withdrawals(call: types.CallbackQuery):
    if call.from_user.id != config.ADMIN_ID:
        return
    reqs = get_pending_withdrawals()
    if not reqs:
        await call.answer("Нет заявок")
        return
    for req in reqs:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"approve_{req[0]}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{req[0]}")]
        ])
        await call.message.answer(f"Заявка #{req[0]} от {req[1]} на {req[2]}⭐", reply_markup=btn)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_withdraw(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    update_withdrawal_status(req_id, "approved")
    await call.answer("✅ Выплачено")
    await call.message.delete()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_withdraw(call: types.CallbackQuery):
    req_id = int(call.data.split("_")[1])
    cursor.execute('SELECT user_id, amount FROM withdrawal_requests WHERE id = ?', (req_id,))
    user_id, amount = cursor.fetchone()
    update_balance(user_id, amount)  # Возвращаем звёзды
    update_withdrawal_status(req_id, "rejected")
    await call.answer("❌ Отклонено")
    await call.message.delete()

# Рассылка, бан, выдача баланса — по аналогии (кратко)
@dp.callback_query(F.data == "admin_give_balance")
async def give_balance_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != config.ADMIN_ID:
        return
    await call.message.answer("🆔 Введите user_id:")
    await state.set_state(AdminStates.waiting_balance_user_id)

# ... (другие админ-функции по желанию расширяются)

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
