
import os
import numpy as np
from PIL import Image, ImageOps # ImageOps для более удобного padding'а
import onnxruntime
from huggingface_hub import hf_hub_download
from transformers import AutoImageProcessor

# --- Конфигурация ---
MODELS_DIR = "models"
IMAGES_DIR = "input_images"
EMBEDDINGS_DIR = "embeddings_padded" # Сохраняем в новую папку, чтобы не путать

ONNX_MODEL_REPO_ID = "onnx-community/dinov2-small-ONNX"
ONNX_MODEL_FILENAME = "onnx/model.onnx"

IMAGE_PROCESSOR_ID = "facebook/dinov2-small"
ONNX_PROVIDERS = ['CPUExecutionProvider']
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

# Целевой размер, на который будут дополнены изображения перед подачей в модель
# Обычно это то, что ожидает image_processor
# Мы можем получить его динамически из image_processor.size
# TARGET_SIZE_H = 224
# TARGET_SIZE_W = 224
# PADDING_COLOR = (0, 0, 0) # Черный цвет для полей

def ensure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Создана директория: {dir_path}")

def download_model_if_needed(repo_id, filename, target_dir):
    model_path = os.path.join(target_dir, filename)
    if not os.path.exists(model_path):
        print(f"Скачивание модели {filename} из {repo_id}...")
        try:
            hf_hub_download(repo_id=repo_id, filename=filename, local_dir=target_dir, local_dir_use_symlinks=False)
            print(f"Модель успешно скачана в: {model_path}")
        except Exception as e:
            print(f"Ошибка при скачивании модели: {e}")
            return None
    else:
        print(f"Модель уже существует: {model_path}")
    return model_path

def pad_image_to_target_size(image_pil, target_height, target_width, padding_color=(0,0,0)):
    """Дополняет PIL изображение полями до target_size, центрируя оригинал."""
    original_width, original_height = image_pil.size

    # Если изображение уже нужного размера или больше, не делаем паддинг, а ресайзим (или можно вызвать ошибку)
    # Для эталонов 93x93 это условие не должно выполняться, если target_size больше
    if original_width == target_width and original_height == target_height:
        return image_pil
    
    # Рассчитываем соотношения сторон
    target_aspect = target_width / target_height
    original_aspect = original_width / original_height

    if original_aspect > target_aspect: # Оригинал шире целевого соотношения -> масштабируем по ширине
        new_width = target_width
        new_height = int(new_width / original_aspect)
    else: # Оригинал выше или такое же соотношение -> масштабируем по высоте
        new_height = target_height
        new_width = int(new_height * original_aspect)
        
    # Масштабируем с сохранением пропорций до размера, который впишется в target_size
    resized_image = image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Создаем новый холст и вставляем отмасштабированное изображение в центр
    padded_image = Image.new(image_pil.mode, (target_width, target_height), padding_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_image.paste(resized_image, (paste_x, paste_y))
    
    return padded_image


def main():
    print("--- Запуск скрипта создания эмбеддингов с паддингом ---")

    ensure_dir_exists(MODELS_DIR)
    ensure_dir_exists(IMAGES_DIR)
    ensure_dir_exists(EMBEDDINGS_DIR)

    onnx_model_path = download_model_if_needed(ONNX_MODEL_REPO_ID, ONNX_MODEL_FILENAME, MODELS_DIR)
    if not onnx_model_path:
        print("Не удалось получить модель ONNX. Завершение работы.")
        return

    try:
        ort_session = onnxruntime.InferenceSession(onnx_model_path, providers=ONNX_PROVIDERS)
        input_name = ort_session.get_inputs()[0].name
        image_processor = AutoImageProcessor.from_pretrained(IMAGE_PROCESSOR_ID)
        # Получаем целевой размер из процессора
        # image_processor.size это словарь, например {'height': 224, 'width': 224} или {'shortest_edge': 224}
        # Для ViT обычно это фиксированный квадратный размер.
        if 'height' in image_processor.size and 'width' in image_processor.size:
            target_h = image_processor.size['height']
            target_w = image_processor.size['width']
        elif 'shortest_edge' in image_processor.size: # Если указана только короткая сторона для ресайза
            # Для простоты, если у нас маленькие query images, мы все равно будем паддить до квадратного размера
            # на котором модель была предобучена (обычно это видно из имени модели patch14_224)
            # Если image_processor.size = {'shortest_edge': 224}, то для DINOv2 это обычно означает,
            # что он сделает ресайз до 224xN или Nx224, а потом может быть паддинг или кроп до квадратного.
            # Для DINOv2 стандартный размер входа обычно квадратный, например 224x224.
            # Проверим имя модели для размера, если image_processor.size не дает явных H, W
            if "224" in IMAGE_PROCESSOR_ID or "224" in ONNX_MODEL_FILENAME: # Грубая проверка
                 target_h, target_w = 224, 224
            elif "256" in IMAGE_PROCESSOR_ID or "256" in ONNX_MODEL_FILENAME:
                 target_h, target_w = 256, 256
            else: # Если не можем определить, ставим дефолтное
                 print("Не удалось определить target_size из image_processor, используется 224x224.")
                 target_h, target_w = 224, 224
        else:
            print("Не удалось определить target_size из image_processor, используется 224x224.")
            target_h, target_w = 224, 224

        print(f"ONNX сессия и процессор загружены. Целевой размер для паддинга: {target_w}x{target_h}")

    except Exception as e:
        print(f"Ошибка при загрузке ONNX или процессора: {e}")
        return

    image_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
    if not image_files:
        print(f"В директории '{IMAGES_DIR}' не найдено изображений.")
        return

    print(f"Найдено изображений для обработки: {len(image_files)}")
    for image_filename in image_files:
        image_path = os.path.join(IMAGES_DIR, image_filename)
        embedding_filename = os.path.splitext(image_filename)[0] + ".npy"
        embedding_path = os.path.join(EMBEDDINGS_DIR, embedding_filename)

        if os.path.exists(embedding_path):
            print(f"Эмбеддинг для '{image_filename}' уже существует, пропуск: {embedding_path}")
            continue

        try:
            print(f"Обработка эталона: {image_filename}")
            img_pil = Image.open(image_path).convert("RGB")
            
            # Паддинг изображения до целевого размера
            img_padded_pil = pad_image_to_target_size(img_pil, target_h, target_w)
            # img_padded_pil.save(f"padded_{image_filename}") # Для отладки, чтобы посмотреть на результат паддинга

            inputs = image_processor(images=img_padded_pil, return_tensors="np")
            onnx_outputs = ort_session.run(None, {input_name: inputs.pixel_values})
            last_hidden_state = onnx_outputs[0]
            embedding = last_hidden_state[0, 0, :] # CLS токен

            np.save(embedding_path, embedding)
            print(f"Эмбеддинг сохранен: {embedding_path} (размерность: {embedding.shape})")
        except Exception as e:
            print(f"Ошибка при обработке изображения '{image_filename}': {e}")

    print("--- Завершение создания эмбеддингов с паддингом ---")

if __name__ == "__main__":
    main()