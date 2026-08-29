from PIL import Image, ImageDraw, ImageFont
import os

def generate_emoji(text: str, is_premium: bool = False) -> str:
    # 1. Задаем холст 512x512 (стандарт для стикеров Telegram)
    size = (512, 512)
    # Прозрачный фон
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 2. Настройка шрифта
    # Пытаемся загрузить шрифт из папки fonts, иначе используем дефолтный
    try:
        # Размер шрифта подбирается для заполнения 512x512
        font = ImageFont.truetype("fonts/Poppins-Bold.ttf", 320)
    except IOError:
        font = ImageFont.load_default()

    # 3. Отрисовка основного текста/эмодзи (сглаживание включено в PIL по умолчанию для TTF)
    # Координаты (256, 256) - центр картинки
    draw.text((256, 256), text, font=font, fill=(0, 0, 0, 255), anchor="mm")

    # 4. Логика PREMIUM-вкладки (добавляем эффекты)
    if is_premium:
        # Пример: Золотая окантовка и "свечение"
        # Для высокого качества рисуем векторные элементы
        draw.rounded_rectangle(
            [20, 20, 492, 492], 
            radius=40, 
            outline=(255, 215, 0, 255), # Золотой цвет
            width=20
        )
        # Если есть готовая картинка короны, ее можно наложить так, 
        # используя LANCZOS для сохранения качества при ресайзе:
        '''
        if os.path.exists("assets/crown.png"):
            crown = Image.open("assets/crown.png").convert("RGBA")
            crown = crown.resize((150, 150), Image.Resampling.LANCZOS)
            img.paste(crown, (180, 20), crown)
        '''

    # 5. Сохранение файла
    output_path = "output_emoji.webp"
    # Сохраняем в формат WebP для Telegram без потери качества (quality=100)
    img.save(output_path, format="WEBP", quality=100, method=6)
    
    return output_path
