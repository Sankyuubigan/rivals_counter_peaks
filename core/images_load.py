from PIL import Image, ImageTk
import os
import sys

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу. """
    try:
        base_path = sys._MEIPASS  # Папка с ресурсами при запуске из .exe
    except AttributeError:
        base_path = os.path.abspath(".")  # Папка с проектом при запуске из .py
    return os.path.join(base_path, relative_path)

# Размеры для разных режимов
SIZES = {
    'max': {'main': (50, 50), 'small': (35, 35)},
    'middle': {'main': (25, 25), 'small': (18, 18)},
    'min': {'main': (25, 25), 'small': (18, 18)} # В min режиме используем те же размеры, что и в middle
}

# Глобальные словари для хранения загруженных изображений разных размеров
loaded_images = {mode: {'main': {}, 'small': {}} for mode in SIZES}
original_images = {} # Для хранения оригиналов PIL Image

def load_original_images():
    """Загружает оригинальные PIL изображения один раз."""
    from heroes_bd import heroes
    if original_images: # Загружаем только если еще не загружены
        return

    print("Loading original images...")
    for hero in heroes:
        try:
            img_path = resource_path(f"resources/{hero.lower().replace(' ', '_')}.png")
            original_images[hero] = Image.open(img_path)
        except FileNotFoundError:
            print(f"Original image for {hero} not found at path: {img_path}")
            original_images[hero] = None
    print("Original images loaded.")


def get_images_for_mode(mode='middle'):
    """Возвращает набор ImageTk изображений для указанного режима."""
    if not original_images:
        load_original_images()

    if mode not in SIZES:
        print(f"Warning: Unknown mode '{mode}'. Using 'middle'.")
        mode = 'middle'

    # Проверяем, загружены ли уже изображения для этого режима
    if loaded_images[mode]['main'] and loaded_images[mode]['small']:
         # Проверяем, все ли герои загружены (на случай добавления новых)
        from heroes_bd import heroes
        if all(hero in loaded_images[mode]['main'] for hero in heroes):
             print(f"Returning cached images for mode: {mode}")
             return loaded_images[mode]['main'], loaded_images[mode]['small']
        else:
             print(f"New heroes detected, regenerating images for mode: {mode}")


    print(f"Generating images for mode: {mode}")
    main_size = SIZES[mode]['main']
    small_size = SIZES[mode]['small']
    current_main_images = {}
    current_small_images = {}

    for hero, img in original_images.items():
        if img:
            try:
                # Основные иконки
                main_img_resized = img.resize(main_size, Image.Resampling.LANCZOS)
                current_main_images[hero] = ImageTk.PhotoImage(main_img_resized)

                # Мелкие иконки
                small_img_resized = img.resize(small_size, Image.Resampling.LANCZOS)
                current_small_images[hero] = ImageTk.PhotoImage(small_img_resized)
            except Exception as e:
                 print(f"Error resizing image for {hero} in mode {mode}: {e}")
                 current_main_images[hero] = None
                 current_small_images[hero] = None
        else:
            current_main_images[hero] = None
            current_small_images[hero] = None

    # Кэшируем результат
    loaded_images[mode]['main'] = current_main_images
    loaded_images[mode]['small'] = current_small_images
    print(f"Images generated and cached for mode: {mode}")

    return current_main_images, current_small_images


# Оставляем старую функцию для обратной совместимости, если где-то используется напрямую,
# но теперь она просто вызывает новую с режимом по умолчанию.
def load_images():
    print("Warning: Direct call to load_images() is deprecated. Use get_images_for_mode().")
    return get_images_for_mode('middle')
