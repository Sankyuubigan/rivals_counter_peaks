import pyautogui
import easyocr
import time
import numpy as np
from PIL import Image
import os

def capture_and_recognize_top_left():
    # Получаем размеры экрана
    screen_width, screen_height = pyautogui.size()
    
    # Рассчитываем размеры области (1/3 ширины, 1/10 высоты)
    crop_width = screen_width // 3
    crop_height = screen_height // 10
    
    # Координаты верхнего левого угла (левый верхний угол экрана)
    crop_x = 0
    crop_y = 0
    
    print(f"Размеры экрана: {screen_width}x{screen_height}")
    print(f"Размеры области для захвата: {crop_width}x{crop_height}")
    
    # Инициализация OCR
    reader = easyocr.Reader(['ru', 'en'])
    
    # Захват всего экрана
    screenshot = pyautogui.screenshot()
    
    # Обрезка нужной области
    cropped = screenshot.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
    
    # # Сохранение обрезанного изображения для отладки
    # debug_filename = "debug_cropped_area.png"
    # cropped.save(debug_filename)
    # print(f"Обрезанное изображение сохранено как: {os.path.abspath(debug_filename)}")
    
    # Преобразование в numpy массив для EasyOCR
    img_array = np.array(cropped)
    
    # Распознавание текста
    results = reader.readtext(img_array)
    
    # Извлечение только текста
    text_parts = []
    for (bbox, text, confidence) in results:
        if confidence > 0.5:  # фильтр по уверенности
            text_parts.append(text)
    
    recognized_text = '\n'.join(text_parts)
    print("\nРаспознанный текст:")
    print(recognized_text)
    print(f"\nКоординаты области: ({crop_x}, {crop_y})")
    
    return recognized_text

if __name__ == "__main__":
    print("Запуск через 3 секунды...")
    time.sleep(3)
    result = capture_and_recognize_top_left()