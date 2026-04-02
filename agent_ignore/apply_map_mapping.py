"""
Скрипт для применения маппинга карт к собранным данным.
Читает JSON-файл со статистикой, заменяет img_map_xxx на правильные названия,
и сохраняет результат.
"""
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("map_mapper")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GAME_ENTITIES_PATH = os.path.join(PROJECT_ROOT, "database", "game_entities_dict.json")


def load_map_filename_mapping():
    """Загружает маппинг img_filename -> correct_name."""
    with open(GAME_ENTITIES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("map_filename_to_name", {})


def apply_map_mapping(data, mapping):
    """Рекурсивно заменяет map_name через маппинг."""
    if isinstance(data, dict):
        if data.get("map_name") and data["map_name"] in mapping:
            old = data["map_name"]
            data["map_name"] = mapping[old]
            logger.info(f"  Заменено: {old} -> {data['map_name']}")
        for key, value in data.items():
            apply_map_mapping(value, mapping)
    elif isinstance(data, list):
        for item in data:
            apply_map_mapping(item, mapping)


def main():
    if len(sys.argv) < 2:
        print("Использование: python apply_map_mapping.py <input_json> [output_json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path

    mapping = load_map_filename_mapping()
    logger.info(f"Загружено {len(mapping)} маппингов карт")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    apply_map_mapping(data, mapping)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Сохранено в {output_path}")


if __name__ == "__main__":
    main()
