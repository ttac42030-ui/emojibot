from PIL import Image, ImageDraw, ImageFont
import os

def generate_emoji(text: str) -> str:
    # Задаем холст 512x512 (стандарт для стикеров Telegram)
    size = (512, 512)
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Настройка шрифта
    try:
        font = ImageFont.truetype("fonts/Poppins-Bold.ttf", 320)
    except IOError:
        font = ImageFont.load_default()

    # Отрисовка текста по центру
    draw.text((256, 256), text, font=font, fill=(0, 0, 0, 255), anchor="mm")

    # Сохранение файла в формат WebP для Telegram
    output_path = "output_emoji.webp"
    img.save(output_path, format="WEBP", quality=100, method=6)
    
    return output_path
