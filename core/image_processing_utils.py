# File: core/image_processing_utils.py
# import cv2 # cv2 не используется в этой версии
# import numpy as np # numpy не используется в этой версии
from PIL import Image, ImageFilter # Используем ImageFilter для UnsharpMask
import logging

def preprocess_image_for_dino(image_pil: Image.Image) -> Image.Image | None:
    """
    Предобрабатывает изображение PIL для последующей подачи в DINOv2.
    Применяет нерезкое маскирование (Unsharp Mask) для усиления деталей.
    Используются "мягкие" параметры, показавшие лучшие результаты.
    Возвращает обработанное изображение PIL или None в случае серьезной ошибки.
    """
    if image_pil is None:
        logging.warning("[ImageProcessing] Получено None изображение для предобработки.")
        return None

    try:
        # 1. Убедимся, что изображение в режиме RGB для корректной работы фильтров Pillow
        image_pil_rgb = None
        if image_pil.mode not in ('RGB', 'L'): 
            if image_pil.mode == 'RGBA' or 'A' in image_pil.getbands():
                background = Image.new("RGB", image_pil.size, (255, 255, 255))
                alpha_channel = None
                if image_pil.mode == 'RGBA':
                    alpha_channel = image_pil.split()[-1] 
                elif 'A' in image_pil.getbands():
                    bands = image_pil.split()
                    for i, band_name in enumerate(image_pil.getbands()):
                        if band_name == 'A':
                            alpha_channel = bands[i]
                            break
                if alpha_channel:
                    background.paste(image_pil, mask=alpha_channel)
                    image_pil_rgb = background
                else:
                    image_pil_rgb = image_pil.convert('RGB')
            else:
                image_pil_rgb = image_pil.convert('RGB')
        elif image_pil.mode == 'L':
             image_pil_rgb = image_pil.convert('RGB')
        else: 
            image_pil_rgb = image_pil
        
        if image_pil_rgb is None:
            logging.error("[ImageProcessing] Не удалось конвертировать изображение в RGB.")
            return None

        # 2. Применение нерезкого маскирования (Unsharp Mask)
        # Используем "мягкие" параметры: radius=1, percent=120, threshold=3
        
        sharpened_image_pil = image_pil_rgb.filter(
            ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3)
        )
        
        # logging.debug("[ImageProcessing] Изображение успешно обработано (Чистый 'мягкий' Unsharp Mask).")
        return sharpened_image_pil

    except Exception as e:
        logging.error(f"[ImageProcessing] Ошибка при предобработке изображения (Чистый 'мягкий' Unsharp Mask): {e}", exc_info=True)
        return None