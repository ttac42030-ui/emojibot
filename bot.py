import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from storage import check_premium, set_premium
from generator import generate_emoji

# Вставь свой токен от BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Клавиатура с вкладками
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать обычный эмодзи 🟢", callback_data="create_basic")],
        [InlineKeyboardButton(text="Создать PREMIUM эмодзи 💎", callback_data="create_premium")],
        [InlineKeyboardButton(text="⭐️ Купить Premium (Демо)", callback_data="buy_premium")]
    ])
    await message.answer(
        "Привет! Я бот для создания кастомных эмодзи.\n"
        "Выбери, какой эмодзи хочешь создать:",
        reply_markup=kb
    )

@dp.callback_query(F.data == "create_basic")
async def process_basic(callback: types.CallbackQuery):
    await callback.answer("Генерируем...")
    # Генерация базового эмодзи
    img_path = generate_emoji("😎", is_premium=False)
    
    # Telegram требует отправлять стикеры в формате .webp
    await callback.message.answer_document(
        document=types.FSInputFile(img_path),
        caption="Твой базовый эмодзи!"
    )

@dp.callback_query(F.data == "create_premium")
async def process_premium(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Проверка статуса в базе данных
    if check_premium(user_id):
        await callback.answer("Генерируем премиум...")
        img_path = generate_emoji("😎", is_premium=True)
        await callback.message.answer_document(
            document=types.FSInputFile(img_path),
            caption="Твой ПРЕМИУМ эмодзи! 💎"
        )
    else:
        # Если нет премиума, предлагаем купить
        await callback.answer("У тебя нет Premium! Нажми 'Купить Premium ⭐️'", show_alert=True)

@dp.callback_query(F.data == "buy_premium")
async def process_buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # В реальном проекте тут будет интеграция с Telegram Stars или ЮKassa
    set_premium(user_id, True)
    await callback.answer("Premium успешно активирован!", show_alert=True)
    await callback.message.answer("Поздравляем! 🥳 Теперь тебе доступны премиум эмодзи 💎")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
