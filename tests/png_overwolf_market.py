import os
import sys

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Ошибка: Не установлена библиотека Pillow.")
    print("Установите её командой: pip install Pillow")
    sys.exit(1)

def generate_icons():
    # Получаем пути к папкам
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_dir = os.path.join(base_path, 'overwolf_app')
    icon_path = os.path.join(app_dir, 'icon.png')

    if not os.path.exists(icon_path):
        print(f"Ошибка: Файл не найден по пути {icon_path}")
        return

    print("Открываем исходный файл...")
    img = Image.open(icon_path).convert("RGBA")

    # 1. Создание launcher_icon.ico (обязательно 4 слоя: 16, 32, 48, 256)
    ico_path = os.path.join(app_dir, 'launcher_icon.ico')
    sizes =[(16, 16), (32, 32), (48, 48), (256, 256)]
    img.save(ico_path, format='ICO', sizes=sizes)
    print(f"Успешно создан: {ico_path} (Слои: {sizes})")

    # 2. Создание IconMouseOver.png (Цветная, 256x256)
    mouseover_path = os.path.join(app_dir, 'IconMouseOver.png')
    img_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    img_256.save(mouseover_path, format='PNG')
    print(f"Успешно создан: {mouseover_path} (Цветная)")

    # 3. Создание IconMouseNormal.png (Черно-белая, 256x256)
    normal_path = os.path.join(app_dir, 'IconMouseNormal.png')
    # Разделяем каналы, чтобы сохранить прозрачность
    r, g, b, a = img_256.split()
    gray = ImageOps.grayscale(img_256)
    # Собираем обратно с оригинальным альфа-каналом
    img_gray_rgba = Image.merge("RGBA", (gray, gray, gray, a))
    img_gray_rgba.save(normal_path, format='PNG')
    print(f"Успешно создан: {normal_path} (Черно-белая)")

    print("\nГенерация иконок завершена! Теперь можно собирать .opk архив.")

if __name__ == "__main__":
    generate_icons()