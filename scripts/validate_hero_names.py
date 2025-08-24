#!/usr/bin/env python
"""
Скрипт для проверки корректности нормализации имен героев
Сравнивает имена файлов в resources/heroes_icons/ с именами в базе данных
"""

import os
import re
import json
import time
from pathlib import Path

def normalize_hero_name(name: str) -> str:
    """Копия функции нормализации из Rust для проверки"""
    if not name:
        return ""

    # Приводим к нижнему регистру
    normalized = name.lower()

    # Удаляем числовые суффиксы типа _1, _2, _v2, _v3
    normalized = re.sub(r"[_ ]*v\d+$", "", normalized)
    normalized = re.sub(r"_\d+$", "", normalized)

    # Удаляем другие общие суффиксы
    suffixes_to_remove = ["_icon", "_template", "_small", "_left", "_right",
                         "_horizontal", "_adv", "_padded"]
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break

    # Оставляем & как есть для некоторых имен типа "Cloak & Dagger"
    # normalized = re.sub(r"[&]", " and ", normalized)

    # Заменяем тире, подчеркивания на пробелы, убираем лишние пробелы
    normalized = re.sub(r"[-_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Капитализируем слова
    parts = normalized.split(' ')
    capitalized = []
    for p in parts:
        if p:
            if len(p) > 0:
                capitalized.append(p[0].upper() + p[1:].lower())

    # Специальная обработка для "Cloak & Dagger"
    result = " ".join(capitalized)
    if result.lower() == "cloak and dagger":
        return "Cloak & Dagger"

    return result

def load_heroes_from_json():
    """Загружает героев из JSON файла"""
    json_path = Path(__file__).parent.parent / "database" / "marvel_rivals_stats_20250810-055947.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return list(data.keys())


def get_icon_files():
    """Получает список файлов иконок"""
    icons_path = Path(__file__).parent.parent / "resources" / "heroes_icons"
    if not icons_path.exists():
        return []

    files = []
    for file_path in icons_path.glob("*.png"):
        # Убираем расширение
        name = file_path.stem
        files.append(name)

    return files

def main():
    print("Проверка корректности нормализации имен героев\n")

    # Загружаем данные только из JSON
    json_heroes = load_heroes_from_json()
    icon_files = get_icon_files()

    print(f"Статистика:")
    print(f"   Героев в базе данных: {len(json_heroes)}")
    print(f"   Файлов иконок: {len(icon_files)}")
    print()

    # Создаем множество для быстрого поиска
    json_heroes_set = set(json_heroes)

    # Проверяем нормализацию файлов
    normalized_files = {}
    successful_matches = []
    failed_matches = []

    print("Проверка нормализации файлов иконок:")
    print("-" * 60)

    for file_name in sorted(icon_files):
        normalized = normalize_hero_name(file_name)
        normalized_files[file_name] = normalized

        # Проверяем совпадение
        if normalized in json_heroes_set:
            successful_matches.append((file_name, normalized))
            print(f"[OK] {file_name} -> {normalized}")
        else:
            failed_matches.append((file_name, normalized))
            print(f"[ERROR] {file_name} -> {normalized} (не найдено в базе)")

    print()
    print("Результаты:")
    print(f"   Успешных сопоставлений: {len(successful_matches)}")
    print(f"   Не найденных в базе: {len(failed_matches)}")

    if failed_matches:
        print("\nПроблемные файлы:")
        for file_name, normalized in failed_matches:
            print(f"   {file_name} -> {normalized}")

            # Ищем похожие имена
            similar = []
            for hero in json_heroes:
                if hero.lower() == normalized.lower():
                    similar.append(hero)
            if similar:
                print(f"      Возможно имелось в виду: {similar[0]}")

    # Проверяем, все ли герои из базы имеют соответствующие файлы
    print("\nПроверка обратного соответствия (герои -> файлы):")
    print("-" * 60)

    heroes_without_icons = []
    for hero in sorted(json_heroes):
        # Ищем файлы, которые после нормализации дают это имя
        found_files = []
        for file_name in icon_files:
            if normalize_hero_name(file_name) == hero:
                found_files.append(file_name)

        if not found_files:
            heroes_without_icons.append(hero)
            print(f"[ERROR] {hero} (нет подходящих файлов)")
        else:
            print(f"[OK] {hero} <- {', '.join(found_files)}")

    print()
    print("Итоговая сводка:")
    print(f"   Всего героев в базе данных: {len(json_heroes)}")
    print(f"   Героев без иконок: {len(heroes_without_icons)}")
    print(f"   Файлов с успешной нормализацией: {len(successful_matches)}")
    print(f"   Файлов с проблемами: {len(failed_matches)}")

    # Проверяем производительность нормализации
    print("\nТестирование производительности нормализации:")

    test_names = list(normalized_files.keys())[:100]  # Тестируем на 100 именах
    start_time = time.time()

    for _ in range(1000):  # 1000 итераций
        for name in test_names:
            normalize_hero_name(name)

    end_time = time.time()
    total_time = end_time - start_time
    per_operation = (total_time / (1000 * len(test_names))) * 1000  # мс на операцию

    print(f"   Время на 1000 операций: {total_time:.3f} сек")
    print(f"   Время на одну операцию: {per_operation:.3f} мс")

if __name__ == "__main__":
    main()