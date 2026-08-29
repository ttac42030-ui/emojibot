import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import StickerFormat, StickerType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputSticker,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from dotenv import load_dotenv

from generator import STYLES, STYLE_BY_KEY, render_emoji, render_previews
import storage

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EXTRA_EMOJI_STARS_PRICE = int(os.getenv("EXTRA_EMOJI_STARS_PRICE", "2"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("emojibot")

router = Router()


class Flow(StatesGroup):
    waiting_nickname = State()
    choosing_style = State()


def sanitize_for_set_name(text: str) -> str:
    """Только латиница/цифры для короткого имени стикер-сета."""
    translit = re.sub(r"[^a-zA-Z0-9]", "", text)
    return translit.lower() or "user"


def styles_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=s.label, callback_data=f"style:{s.key}")] for s in STYLES]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buy_more_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=s.label, callback_data=f"buy:{s.key}")] for s in STYLES]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! 👋 Я сделаю тебе анимированный* эмодзи-пак под твой ник.\n\n"
        "Напиши свой ник (до 10 символов), и я покажу варианты расцветок.\n\n"
        "Первый эмодзи — бесплатно, каждый следующий — "
        f"{EXTRA_EMOJI_STARS_PRICE}⭐ Telegram Stars."
    )
    await state.set_state(Flow.waiting_nickname)


@router.message(Flow.waiting_nickname, F.text)
async def got_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    if not (1 <= len(nickname) <= 20):
        await message.answer("Ник должен быть от 1 до 20 символов. Попробуй ещё раз.")
        return

    await state.update_data(nickname=nickname)
    await message.answer("Генерирую варианты расцветок… 🎨")

    previews = render_previews(nickname)
    media = [
        BufferedInputFile(png_bytes, filename=f"{style.key}.png")
        for style, png_bytes in previews
    ]
    for style, file in zip((s for s, _ in previews), media):
        await message.answer_photo(photo=file, caption=style.label)

    await message.answer("Выбери расцветку для своего эмодзи-пака:", reply_markup=styles_keyboard())
    await state.set_state(Flow.choosing_style)


@router.callback_query(Flow.choosing_style, F.data.startswith("style:"))
async def style_chosen(call: CallbackQuery, state: FSMContext, bot: Bot):
    style_key = call.data.split(":", 1)[1]
    data = await state.get_data()
    nickname = data["nickname"]
    user_id = call.from_user.id

    await call.answer("Собираю пак…")
    png_bytes = render_emoji(nickname, style_key)

    me = await bot.get_me()
    set_name = f"{sanitize_for_set_name(nickname)}{user_id}_by_{me.username}"

    try:
        uploaded = await bot.upload_sticker_file(
            user_id=user_id,
            sticker=BufferedInputFile(png_bytes, filename="emoji.png"),
            sticker_format=StickerFormat.STATIC,
        )
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=set_name,
            title=f"{nickname} emoji",
            stickers=[InputSticker(sticker=uploaded.file_id, format=StickerFormat.STATIC, emoji_list=["✨"])],
            sticker_type=StickerType.CUSTOM_EMOJI,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to create sticker set")
        await call.message.answer(
            "Не получилось создать пак 😔\n"
            f"Ошибка Telegram API: {exc}\n\n"
            "Обычно это значит, что нужно поменять имя пака (уже занято) — попробуй ещё раз через /start."
        )
        return

    storage.update_user(
        user_id,
        nickname=nickname,
        sticker_set_name=set_name,
        free_used=True,
        emoji_count=1,
    )

    await call.message.answer(
        f"Готово! 🎉 Твой пак: https://t.me/addemoji/{set_name}\n\n"
        f"Хочешь добавить ещё эмодзи в другой расцветке? Это {EXTRA_EMOJI_STARS_PRICE}⭐ за штуку.",
        reply_markup=buy_more_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data.startswith("buy:"))
async def buy_more(call: CallbackQuery, bot: Bot):
    style_key = call.data.split(":", 1)[1]
    user = storage.get_user(call.from_user.id)
    if not user.get("sticker_set_name"):
        await call.answer("Сначала создай пак через /start", show_alert=True)
        return

    await call.answer()
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"Эмодзи «{STYLE_BY_KEY[style_key].label}»",
        description="Дополнительный эмодзи в твой пак",
        payload=f"extra_emoji:{style_key}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label="Эмодзи", amount=EXTRA_EMOJI_STARS_PRICE)],
        provider_token="",  # для Stars provider_token не нужен
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    style_key = payload.split(":", 1)[1]
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if not user.get("sticker_set_name") or not user.get("nickname"):
        await message.answer("Не нашёл твой пак — напиши /start и начни заново, вернём звёзды в поддержке.")
        return

    png_bytes = render_emoji(user["nickname"], style_key)
    try:
        uploaded = await bot.upload_sticker_file(
            user_id=user_id,
            sticker=BufferedInputFile(png_bytes, filename="emoji.png"),
            sticker_format=StickerFormat.STATIC,
        )
        await bot.add_sticker_to_set(
            user_id=user_id,
            name=user["sticker_set_name"],
            sticker=InputSticker(sticker=uploaded.file_id, format=StickerFormat.STATIC, emoji_list=["✨"]),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to add sticker")
        await message.answer(f"Оплата прошла, но добавить эмодзи не вышло: {exc}\nНапиши в поддержку.")
        return

    storage.update_user(user_id, emoji_count=user.get("emoji_count", 0) + 1)
    await message.answer(
        f"Добавил! ✨ Пак обновлён: https://t.me/addemoji/{user['sticker_set_name']}",
        reply_markup=buy_more_keyboard(),
    )


WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # напр. https://your-app.onrender.com
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", "10000"))


async def run_polling():
    """Локальный запуск (на своём ПК/сервере с постоянным процессом)."""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


def run_webhook():
    """
    Режим для бесплатных хостингов вроде Render: бот поднимает
    HTTP-сервер и Telegram сам присылает обновления на WEBHOOK_URL.
    """
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def on_startup(_):
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)

    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")
    if WEBHOOK_URL:
        run_webhook()
    else:
        asyncio.run(run_polling())
