import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, LabeledPrice
from storage import has_free_attempt, use_free_attempt
from generator import generate_emoji

# Получаем токен из переменных окружения на Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("ВНИМАНИЕ: BOT_TOKEN не найден в переменных окружения!")
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # Заглушка, если переменная не подтянется

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Цена в Telegram Stars (2 звезды)
PRICE = [LabeledPrice(label="Эмодзи", amount=2)]

# Твои готовые видео-файлы
PREMIUM_EMOJIS = {
    "fire": {"title": "🔥 Пламя", "file": "premium_assets/fire.webm"},
    "crown": {"title": "👑 Корона", "file": "premium_assets/crown.webm"}
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    free = has_free_attempt(message.from_user.id)
    btn_text = "Создать эмодзи (Бесплатно) 🎁" if free else "Создать эмодзи (2 ⭐️)"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data="buy_basic")],
        [InlineKeyboardButton(text="💎 Премиум эмодзи (2 ⭐️)", callback_data="premium_menu")]
    ])
    await message.answer("Привет! Я бот для создания кастомных эмодзи. Выбери нужный раздел:", reply_markup=kb)

@dp.callback_query(F.data == "buy_basic")
async def process_basic(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if has_free_attempt(user_id):
        await callback.answer("Генерируем бесплатный эмодзи...")
        use_free_attempt(user_id)
        img_path = generate_emoji("😎")
        await callback.message.answer_document(FSInputFile(img_path), caption="Твой бесплатный эмодзи! 🎁")
    else:
        # Отправляем счет на 2 звезды, если бесплатная попытка потрачена
        await bot.send_invoice(
            chat_id=user_id,
            title="Базовый эмодзи",
            description="Оплата генерации кастомного эмодзи",
            payload="basic",
            provider_token="", # Для звезд токен оставляем пустым
            currency="XTR",
            prices=PRICE
        )

@dp.callback_query(F.data == "premium_menu")
async def premium_menu(callback: types.CallbackQuery):
    buttons = []
    for key, data in PREMIUM_EMOJIS.items():
        buttons.append([InlineKeyboardButton(text=f"{data['title']} - 2 ⭐️", callback_data=f"buy_prem_{key}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("✨ Выбери анимированный премиум эмодзи:", reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_prem_"))
async def process_premium_buy(callback: types.CallbackQuery):
    emoji_key = callback.data.replace("buy_prem_", "")
    # Отправляем счет на 2 звезды за премиум эмодзи
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=PREMIUM_EMOJIS[emoji_key]["title"],
        description="Покупка анимированного премиум эмодзи",
        payload=f"prem_{emoji_key}",
        provider_token="",
        currency="XTR",
        prices=PRICE
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    
    if payload == "basic":
        img_path = generate_emoji("😎")
        await message.answer_document(FSInputFile(img_path), caption="Спасибо за покупку! Твой эмодзи ⭐️")
    elif payload.startswith("prem_"):
        emoji_key = payload.replace("prem_", "")
        file_path = PREMIUM_EMOJIS[emoji_key]["file"]
        if os.path.exists(file_path):
            await message.answer_sticker(FSInputFile(file_path))
        else:
            await message.answer("⚠️ Файл эмодзи пока не загружен на сервер (папка premium_assets).")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
