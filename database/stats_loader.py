# File: database/stats_loader.py
import json
import importlib.util
import os
import sys
import logging

def _get_database_path(relative_path):
    """Получает абсолютный путь к файлу в директории database."""
    try:
        # Если приложение "заморожено" PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Обычный запуск .py файла
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Собираем путь к файлу внутри директории database
    return os.path.join(base_path, 'database', relative_path)

def load_matchups_data(file_name="marvel_rivals_stats_20250810-055947.json"):
    """Загружает данные о противостояниях героев из JSON файла."""
    file_path = _get_database_path(file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Преобразуем данные в формат {герой: [список противостояний]}
        matchups = {}
        for hero_name, hero_stats in data.items():
            matchups[hero_name] = hero_stats.get("opponents", [])
        return matchups
    except FileNotFoundError:
        logging.error(f"[StatsLoader] Файл данных '{file_path}' не найден.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"[StatsLoader] Ошибка декодирования JSON из файла '{file_path}'.")
        return {}

def load_hero_stats(file_name="marvel_rivals_stats_20250810-055947.json"):
    """Загружает общую статистику героев (винрейт, пикрейт) из JSON файла."""
    file_path = _get_database_path(file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        hero_stats = {}
        for hero_name, hero_data in data.items():
            hero_stats[hero_name] = {
                "win_rate": hero_data.get("win_rate", "0%"),
                "pick_rate": hero_data.get("pick_rate", "0%"),
                "matches": hero_data.get("matches", "0")
            }
        return hero_stats
    except FileNotFoundError:
        logging.error(f"[StatsLoader] Файл статистики '{file_path}' не найден.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"[StatsLoader] Ошибка декодирования JSON из файла '{file_path}'.")
        return {}

def load_hero_roles(file_name="roles_and_groups.py"):
    """Загружает роли героев из файла roles_and_groups.py."""
    file_path = _get_database_path(file_name)
    if not os.path.exists(file_path):
        logging.error(f"[StatsLoader] Файл ролей '{file_path}' не найден.")
        return {}
        
    try:
        spec = importlib.util.spec_from_file_location("roles_and_groups", file_path)
        roles_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(roles_module)
        
        roles_dict = roles_module.hero_roles
        
        hero_roles_map = {}
        for role, heroes in roles_dict.items():
            for hero in heroes:
                hero_roles_map[hero] = role
        return hero_roles_map
    except Exception as e:
        logging.error(f"[StatsLoader] Ошибка при загрузке ролей из '{file_path}': {e}")
        return {}

def get_all_heroes(matchups_data):
    """Возвращает список всех героев из ключей данных о противостояниях."""
    if not matchups_data:
        logging.warning("[StatsLoader] matchups_data пуст, невозможно получить список героев.")
        return []
    return list(matchups_data.keys())