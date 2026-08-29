"""
Генерация картинок для custom emoji (100x100, статичный PNG).

Никакого стороннего AI-сервиса не используется — дизайн рисуется
программно с помощью Pillow: диагональный градиент из пары цветов
стиля + ник пользователя, вписанный по центру.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_PATH = "fonts/Poppins-Bold.ttf"
EMOJI_SIZE = 100  # Telegram требует ровно 100x100 для custom emoji


@dataclass(frozen=True)
class Style:
    key: str
    label: str          # то, что видит пользователь на кнопке
    color_a: str         # верхний угол градиента
    color_b: str         # нижний угол градиента
    text_color: str = "#FFFFFF"


# color_a — верх градиента (светлее), color_b — низ (темнее),
# как у классических глянцевых app-кнопок.
STYLES = [
    Style("black_gray", "⚫ Чёрно-серый", "#6b6b70", "#141416"),
    Style("black_white", "⚪ Чёрно-белый", "#ffffff", "#3a3a3d", text_color="#1c1c1e"),
    Style("white_purple", "🟣 Бело-фиолетовый", "#c9aaff", "#5b21d6"),
    Style("cyber", "🔵 Кибер", "#5fe3ff", "#0a3b4a"),
    Style("red_glossy", "🔴 Красный", "#ff6b5e", "#8f0f0a"),
    Style("gold", "🟡 Золото", "#ffe38a", "#8a5a00"),
]
STYLE_BY_KEY = {s.key: s for s in STYLES}


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _make_gradient(size: int, color_a: str, color_b: str) -> Image.Image:
    """Диагональный линейный градиент color_a -> color_b."""
    a = _hex_to_rgb(color_a)
    b = _hex_to_rgb(color_b)
    base = Image.new("RGB", (size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return base


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_height: int) -> ImageFont.FreeTypeFont:
    size = max_height
    while size > 8:
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= max_width and h <= max_height:
            return font
        size -= 2
    return ImageFont.truetype(FONT_PATH, 8)


def _vertical_gradient(size: int, top: str, bottom: str) -> Image.Image:
    a, b = _hex_to_rgb(top), _hex_to_rgb(bottom)
    base = Image.new("RGB", (1, size))
    px = base.load()
    for y in range(size):
        t = y / (size - 1)
        px[0, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return base.resize((size, size))


def render_emoji(nickname: str, style_key: str, *, supersample: int = 4) -> bytes:
    """
    Рисует один статичный custom-emoji (PNG, 100x100): глянцевая
    скруглённая "кнопка" с бликом сверху (в духе классических
    app-иконок) и ником по центру.
    """
    style = STYLE_BY_KEY[style_key]
    size = EMOJI_SIZE * supersample
    radius = int(size * 0.24)

    # 1. Форма — скруглённый квадрат с вертикальным градиентом
    #    (светлее сверху, темнее снизу — как объёмная кнопка).
    shape_mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shape_mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)

    gradient = _vertical_gradient(size, style.color_a, style.color_b).convert("RGBA")
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), shape_mask)

    # 2. Глянцевый блик сверху — полупрозрачный белый эллипс, размытый
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse(
        (size * 0.06, -size * 0.35, size * 0.94, size * 0.55),
        fill=(255, 255, 255, 130),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(size // 22))
    highlight.putalpha(Image.composite(highlight.split()[3], Image.new("L", (size, size), 0), shape_mask))
    img = Image.alpha_composite(img, highlight)

    # 3. Тонкая тёмная обводка по контуру для объёма
    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle(
        (size * 0.015, size * 0.015, size - size * 0.015, size - size * 0.015),
        radius=radius,
        outline=(0, 0, 0, 90),
        width=max(2, size // 60),
    )
    img = Image.alpha_composite(img, border)

    # 4. Ник по центру
    draw = ImageDraw.Draw(img)
    text = nickname.strip()[:10] or "?"
    padding = int(size * 0.20)
    font = _fit_font(draw, text, size - 2 * padding, size - 2 * padding)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1])

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((pos[0], pos[1] + size * 0.02), text, font=font, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(size // 50))
    img = Image.alpha_composite(img, shadow)

    draw = ImageDraw.Draw(img)
    draw.text(pos, text, font=font, fill=style.text_color)

    img = img.resize((EMOJI_SIZE, EMOJI_SIZE), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_previews(nickname: str) -> list[tuple[Style, bytes]]:
    """Превью для всех стилей — используется на экране выбора."""
    return [(style, render_emoji(nickname, style.key)) for style in STYLES]
