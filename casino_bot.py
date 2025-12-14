import asyncio
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ================= НАСТРОЙКИ =================

API_TOKEN = "8575204592:AAF5_Ny1UgMMgEFAyh2aPE4jC-4Ja-egZ_s"
ADMIN_IDS = {8264612178}  # ВСТАВЬ СВОЙ TG ID
START_BALANCE = 1000

# ================= БОТ =================

bot = Bot(API_TOKEN)
dp = Dispatcher()

# ================= ДАННЫЕ =================

users = {}
deposit_requests = {}
states = {}

games = {
    "slots": {"name": "🎰 Слоты", "chance": 40, "mult": 3},
    "dice": {"name": "🎲 Кости", "chance": 50, "mult": 2},
    "guess": {"name": "🎯 Угадай число", "chance": 20, "mult": 5},
    "roulette": {"name": "🎡 Рулетка", "chance": 45, "mult": 2},
    "21": {"name": "🃏 21 очко", "chance": 48, "mult": 2},
}

# ================= ВСПОМОГАТЕЛЬНЫЕ =================

def get_user(uid: int):
    if uid not in users:
        users[uid] = {
            "balance": START_BALANCE,
            "history": [],
            "banned": False
        }
    return users[uid]

# ================= КЛАВИАТУРЫ =================

def main_menu(is_admin=False):
    kb = ReplyKeyboardBuilder()
    kb.button(text="🎮 Игры")
    kb.button(text="👤 Личный кабинет")
    kb.row()
    kb.button(text="➕ Пополнение")
    if is_admin:
        kb.button(text="👑 Админ-панель")
    return kb.as_markup(resize_keyboard=True)

def games_menu():
    kb = InlineKeyboardBuilder()
    for k, g in games.items():
        kb.button(text=g["name"], callback_data=f"game_{k}")
    return kb.as_markup()

def bets_menu(game):
    kb = InlineKeyboardBuilder()
    for bet in [50, 100, 250, 500]:
        kb.button(text=f"{bet}", callback_data=f"bet_{game}_{bet}")
    return kb.as_markup()

def admin_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📋 Пользователи")
    kb.button(text="💰 Заявки")
    kb.row()
    kb.button(text="⚙️ Шансы")
    kb.button(text="🚫 Бан / Разбан")
    kb.row()
    kb.button(text="⬅️ Назад")
    return kb.as_markup(resize_keyboard=True)

# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):
    user = get_user(message.from_user.id)
    if user["banned"]:
        await message.answer("🚫 Вы забанены.")
        return
    await message.answer(
        f"🎰 Добро пожаловать!\nБаланс: {user['balance']}",
        reply_markup=main_menu(message.from_user.id in ADMIN_IDS)
    )

# ================= ИГРЫ =================

@dp.message(F.text == "🎮 Игры")
async def show_games(message: Message):
    await message.answer("Выберите игру:", reply_markup=games_menu())

@dp.callback_query(F.data.startswith("game_"))
async def choose_bet(callback: CallbackQuery):
    game = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"{games[game]['name']}\nВыберите ставку:",
        reply_markup=bets_menu(game)
    )

@dp.callback_query(F.data.startswith("bet_"))
async def play(callback: CallbackQuery):
    _, game, bet = callback.data.split("_")
    bet = int(bet)
    user = get_user(callback.from_user.id)

    if user["balance"] < bet:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    user["balance"] -= bet
    await callback.message.edit_text("⏳ Играем...")
    await asyncio.sleep(1.2)

    win = random.randint(1, 100) <= games[game]["chance"]

    if win:
        prize = bet * games[game]["mult"]
        user["balance"] += prize
        user["history"].append(f"{games[game]['name']} +{prize}")
        text = f"🎉 Победа! +{prize}"
    else:
        user["history"].append(f"{games[game]['name']} -{bet}")
        text = f"😢 Проигрыш -{bet}"

    await callback.message.edit_text(f"{text}\nБаланс: {user['balance']}")

# ================= ЛИЧНЫЙ КАБИНЕТ =================

@dp.message(F.text == "👤 Личный кабинет")
async def cabinet(message: Message):
    user = get_user(message.from_user.id)
    history = "\n".join(user["history"][-5:]) or "Пусто"
    await message.answer(
        f"💰 Баланс: {user['balance']}\n\n📜 История:\n{history}"
    )

# ================= ПОПОЛНЕНИЕ =================

@dp.message(F.text == "➕ Пополнение")
async def deposit(message: Message):
    states[message.from_user.id] = "deposit"
    await message.answer("Введите сумму пополнения:")

@dp.message(F.text.regexp(r"^\d+$"))
async def process_deposit(message: Message):
    if states.get(message.from_user.id) != "deposit":
        return
    amount = int(message.text)
    deposit_requests[message.from_user.id] = amount
    states.pop(message.from_user.id)
    await message.answer("✅ Заявка отправлена администратору")

    for admin in ADMIN_IDS:
        await bot.send_message(admin, f"💰 Заявка от {message.from_user.id}: {amount}")

# ================= АДМИН =================

@dp.message(F.text == "👑 Админ-панель")
async def admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_menu())

@dp.message(F.text == "📋 Пользователи")
async def admin_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = "\n".join([f"{uid}: {u['balance']}" for uid, u in users.items()])
    await message.answer(text or "Нет пользователей")

@dp.message(F.text == "💰 Заявки")
async def admin_deposits(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not deposit_requests:
        await message.answer("Заявок нет")
        return

    kb = InlineKeyboardBuilder()
    for uid, amount in deposit_requests.items():
        kb.button(text=f"{uid} | {amount}", callback_data=f"dep_{uid}")
    await message.answer("Выберите заявку:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("dep_"))
async def deposit_actions(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    amount = deposit_requests[uid]

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"ok_{uid}")
    kb.button(text="❌ Отклонить", callback_data=f"no_{uid}")

    await callback.message.edit_text(
        f"Заявка от {uid}\nСумма: {amount}",
        reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data.startswith("ok_"))
async def deposit_ok(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    amount = deposit_requests.pop(uid)

    users[uid]["balance"] += amount
    users[uid]["history"].append(f"Пополнение +{amount}")
    await callback.message.edit_text("✅ Пополнение подтверждено")

@dp.callback_query(F.data.startswith("no_"))
async def deposit_no(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    deposit_requests.pop(uid)
    users[uid]["history"].append("Пополнение отклонено")
    await callback.message.edit_text("❌ Пополнение отклонено")

@dp.message(F.text == "⚙️ Шансы")
async def chances_menu(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardBuilder()
    for k, g in games.items():
        kb.button(text=f"{g['name']} ({g['chance']}%)", callback_data=f"chance_{k}")
    await message.answer("Выберите игру:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("chance_"))
async def set_chance(callback: CallbackQuery):
    game = callback.data.split("_")[1]
    states[callback.from_user.id] = f"chance_{game}"
    await callback.message.edit_text("Введите шанс (1-100):")

@dp.message(F.text.regexp(r"^\d+$"))
async def save_chance(message: Message):
    state = states.get(message.from_user.id)
    if not state or not state.startswith("chance_"):
        return
    game = state.split("_")[1]
    val = int(message.text)

    if not 1 <= val <= 100:
        await message.answer("Введите число от 1 до 100")
        return

    games[game]["chance"] = val
    states.pop(message.from_user.id)
    await message.answer(f"✅ Шанс обновлён: {val}%")

@dp.message(F.text == "⬅️ Назад")
async def back(message: Message):
    await message.answer("Главное меню", reply_markup=main_menu(message.from_user.id in ADMIN_IDS))

# ================= ЗАПУСК =================

async def main():
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
