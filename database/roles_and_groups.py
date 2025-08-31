
# Файл: database/roles_and_groups.py
# Модуль ролей героев Marvel Rivals (новый формат)

import json

# Роли героев загружаются из JSON
hero_roles = {}

def load_hero_roles():
    """
    Загружает роли героев из database/roles.json

    Returns:
        dict: Словарь ролей в формате {role_name: [hero_list]}
    """
    global hero_roles
    try:
        with open("database/roles.json", 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Конвертируем имена героев в внутренний формат для совместимости
            # Словарь маппинга для конверсии названий героев
            name_mapping = {
                "Black Widow": "Widow",
                "Iron Fist": "Fister",
                "Jeff The Land Shark": "Jeff",
                "Spider Man": "SpiderMan",
                "Star Lord": "StarLord",
                "Rocket Raccoon": "Rocket Racoon",
                "Doctor Strange": "Doctor Strange",
                "The Thing": "The Thing",
                "Human Torch": "Human Torch",
                "Mister Fantastic": "Mister Fantastic",
                "Winter Soldier": "Winter Soldier",
                "Squirrel Girl": "Squirrel Girl",
                "Scarlet Witch": "Witch",
                "Black Panther": "Black Panther",
                "Iron Man": "Iron Man",
                "Captain America": "Captain America",
                "Hawkeye": "Hawkeye",
                "The Punisher": "Punisher",
                "Moon Knight": "Moon Knight",
                "Phoenix": "Phoenix",
                "Blade": "Blade"
            }

            # Преобразуем роли в совместимый формат
            for role, heroes_list in data.items():
                # Конвертируем имена героев
                converted_heroes = []
                for hero in heroes_list:
                    converted_name = name_mapping.get(hero, hero)
                    converted_heroes.append(converted_name)

                hero_roles[role] = converted_heroes

        print(f"Загружены роли для {len(data)} групп героев")
        return hero_roles

    except FileNotFoundError:
        print("Файл database/roles.json не найден, используем базовые роли")
        hero_roles = {
            "Vanguard": ["Hulk", "Thor", "The Thing", "Venom", "Captain America"],
            "Strategist": ["Groot", "Doctor Strange", "Mr Fantastic"],
            "Duelist": ["Iron Man", "Widow", "Hawkeye", "Punisher", "Moon Knight"]
        }
        return hero_roles
    except Exception as e:
        print(f"Ошибка загрузки ролей: {e}")
        hero_roles = {
            "Vanguard": ["Hulk", "Thor", "The Thing"],
            "Strategist": ["Groot", "Doctor Strange"],
            "Duelist": ["Iron Man", "Captain America"]
        }
        return hero_roles

# Загружаем роли при инициализации модуля
hero_roles = load_hero_roles()

# Compatility functions (для старого кода)
def get_hero_role(hero):
    """Получить роль героя"""
    for role, heroes_list in hero_roles.items():
        if hero in heroes_list:
            return role
    return "unknown"

