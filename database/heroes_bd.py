# File: database/heroes_bd.py
# Новой модуль для работы с базой данных героев в новом формате JSON

import json
import os
from database.roles_and_groups import hero_roles  # Доступ роли для совместимости

# Глобальные переменные для совместимости с существующим кодом
heroes = []
heroes_counters = {}
heroes_compositions = {}


def load_matchups_data(file_path="database/marvel_rivals_stats_20250831-030213.json"):
    """
    Загружает данные о матчапах из нового JSON файла.

    Args:
        file_path (str): Путь к файлу с данными матчапов

    Returns:
        dict: Словарь {hero_name: opponents_data}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Преобразуем данные в старый формат для совместимости с существующим кодом
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
            "Cloak Dagger": "Cloak and Dagger",
            "Invisible Woman": "Invisible Woman",
            "Adam Warlock": "Adam Warlock",
            "Phoenix": "Phoenix",
            "Blade": "Blade"
        }

        old_format_data = {}
        for hero_name, hero_stats in data.items():
            internal_hero_name = name_mapping.get(hero_name, hero_name)
            old_format_data[internal_hero_name] = hero_stats.get("opponents", [])

        print(f"Загружены матчап данные для {len(old_format_data)} героев")
        return old_format_data
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка при чтении JSON: {e}")
        return {}


def load_hero_stats(file_path="database/marvel_rivals_stats_20250831-030213.json"):
    """
    Загружает статистику героев из нового JSON файла.

    Args:
        file_path (str): Путь к файлу с данными матчапов

    Returns:
        dict: Словарь {hero_name: {'win_rate': float, 'pick_rate': float, 'matches': int}}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

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
            "Cloak Dagger": "Cloak and Dagger",
            "Invisible Woman": "Invisible Woman",
            "Adam Warlock": "Adam Warlock",
            "Phoenix": "Phoenix",
            "Blade": "Blade"
        }

        hero_stats = {}
        for hero_name, hero_data in data.items():
            try:
                win_rate = float(hero_data["win_rate"].replace('%', '')) / 100
                pick_rate = float(hero_data["pick_rate"].replace('%', '')) / 100
                matches_str = hero_data["matches"].replace(',', '')
                matches = int(matches_str)

                internal_hero_name = name_mapping.get(hero_name, hero_name)
                hero_stats[internal_hero_name] = {
                    "win_rate": win_rate,
                    "pick_rate": pick_rate,
                    "matches": matches
                }
            except (KeyError, ValueError) as e:
                print(f"Пропуск героя {hero_name}: {e}")
                continue

        print(f"Загружена статистика для {len(hero_stats)} героев")
        return hero_stats

    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except Exception as e:
        print(f"Ошибка загрузки статистики: {e}")
        return {}


def convert_hero_names_opponents(data):
    """
    Конвертирует имена оппонентов для соответствия внутренней структуре.

    Args:
        data (dict): Данные матчапов из JSON

    Returns:
        dict: Конвертированные данные
    """
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
        "Cloak Dagger": "Cloak and Dagger",
        "Invisible Woman": "Invisible Woman",
        "Adam Warlock": "Adam Warlock",
        "Phoenix": "Phoenix",
        "Blade": "Blade"
    }

    converted_data = {}
    for hero_name, opponents_list in data.items():
        # Конвертируем имя героя
        internal_hero_name = name_mapping.get(hero_name, hero_name)

        # opponents_list уже список матчапов, конвертируем имена внутри каждого матчапа
        converted_opponents = []
        for opponent in opponents_list:
            opponent_name = opponent["opponent"]
            internal_opponent_name = name_mapping.get(opponent_name, opponent_name)
            converted_opponent = opponent.copy()
            converted_opponent["opponent"] = internal_opponent_name
            converted_opponents.append(converted_opponent)

        converted_data[internal_hero_name] = converted_opponents

    print(f"Конвертированы имена для {len(converted_data)} матчапов")
    return converted_data


def load_compositions_data(file_path="database/heroes_compositions.json"):
    """
    Загружает данные о синергиях героев из JSON файла.

    Args:
        file_path (str): Путь к файлу с данными синергий

    Returns:
        dict: Словарь синергий {hero_name: [synergy_heroes]}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Конвертируем имена героев
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
            "Ultron": "Ultron",
            "Adam Warlock": "Adam Warlock",
            "Wolverine": "Wolverine",
            "Magik": "Magik",
            "Loki": "Loki",
            "Cloak and Dagger": "Cloak and Dagger",
            "Mantis": "Mantis",
            "Luna Snow": "Luna Snow",
            "Invisible Woman": "Invisible Woman",
            "Storm": "Storm",
            "Namor": "Namor",
            "Psylocke": "Psylocke",
            "Venom": "Venom",
            "Blade": "Blade",
            "Phoenix": "Phoenix"
        }

        compositions_converted = {}
        for hero_name, synergies in data.items():
            # Конвертируем имя героя
            internal_hero_name = name_mapping.get(hero_name, hero_name)

            # Конвертируем имена в синергиях
            converted_synergies = []
            for synergy in synergies:
                converted_name = name_mapping.get(synergy, synergy)
                converted_synergies.append(converted_name)

            compositions_converted[internal_hero_name] = converted_synergies

        print(f"Загружены синергии для {len(compositions_converted)} героев")
        return compositions_converted

    except FileNotFoundError:
        print(f"Файл {file_path} не найден, возвращаем пустые синергии")
        return {}
    except Exception as e:
        print(f"Ошибка загрузки синергий: {e}")
        return {}


def calculate_team_counters(enemy_team, matchups_data, hero_roles, method="avg", weighting="equal"):
    """
    Рассчитывает рейтинг героев против указанной команды врагов.

    Args:
        enemy_team (list): Список вражеских героев
        matchups_data (dict): Данные матчапов героев
        hero_roles (dict): Роли героев
        method (str): Метод агрегации ('sum' или 'avg')
        weighting (str): Метод взвешивания ('equal' или 'matches')

    Returns:
        list: Список [(hero, rating), ...] отсортированный по убыванию рейтинга
    """
    # Проверяем корректность входных данных
    if not enemy_team:
        raise ValueError("Список вражеских героев не может быть пустым")
    if len(enemy_team) > 6:
        raise ValueError("Максимальное количество вражеских героев - 6")
    if method not in ['sum', 'avg']:
        raise ValueError("Метод агрегации должен быть 'sum' или 'avg'")
    if weighting not in ['equal', 'matches']:
        raise ValueError("Метод взвешивания должен быть 'equal' или 'matches'")

    hero_scores = []

    print(f"[DEBUG] calculate_team_counters called with enemy_team: {enemy_team}")
    print(f"[DEBUG] Total heroes in matchups_data: {len(matchups_data)}")

    # Проходим по каждому герою в базе данных
    for hero, matchups in matchups_data.items():
        total_weighted_difference = 0
        total_weight = 0
        found_matchups = 0
        total_weighted_difference = 0
        total_weight = 0
        found_matchups = 0

        # Проходим по каждому вражескому герою
        for enemy in enemy_team:
            print(f"[DEBUG] {hero}: Checking against enemy {enemy}")
            matchups_list = matchups
            print(f"[DEBUG] {hero}: Found {len(matchups_list)} total opponents")
            # Ищем матчап против этого врага
            for matchup in matchups_list:
                # Сравниваем имена, игнорируя регистр и возможные различия
                if matchup["opponent"].lower() == enemy.lower():
                    print(f"[DEBUG] Found matchup for {hero} vs {enemy}: {matchup}")
                    # Преобразуем строку difference в число
                    diff_str = matchup["difference"].strip().rstrip('%')  # Убираем '%' перед парсингом
                    try:
                        difference = -float(diff_str)  # Инвертируем так как большее число лучше
                        print(f"[DEBUG] Calculated difference: {difference}")
                    except ValueError:
                        print(f"[DEBUG] Invalid difference format after removing %: '{diff_str}'")
                        continue

                    # Определяем вес
                    weight = 1
                    if weighting == "matches" and "matches" in matchup:
                        try:
                            weight = int(matchup["matches"])
                        except (ValueError, KeyError):
                            pass

                    total_weighted_difference += difference * weight
                    total_weight += weight
                    found_matchups += 1
                    print(f"[DEBUG] Added matchup: total_weighted={total_weighted_difference}, total_weight={total_weight}")
                    break

        # Пропускаем героев без данных
        if found_matchups == 0:
            print(f"[DEBUG] {hero}: No matchups found (skipping)")
            continue
        print(f"[DEBUG] {hero}: Found {found_matchups} matchups, total_diff={total_weighted_difference}, total_weight={total_weight}")

        # Рассчитываем итоговый рейтинг
        if total_weight > 0:
            if method == "sum":
                # Нормализуем к среднему для справедливого сравнения
                rating = total_weighted_difference / total_weight * len(enemy_team)
            else:  # avg
                rating = total_weighted_difference / total_weight
        else:
            rating = 0

        hero_scores.append((hero, rating))

    # Сортируем по рейтингу в порядке убывания
    hero_scores.sort(key=lambda x: x[1], reverse=True)

    print(f"[DEBUG] calculate_team_counters: Final hero_scores (top 10): {hero_scores[:10]}")
    # Подробные логи для топ героев
    for i, (hero, rating) in enumerate(hero_scores[:10], 1):
        print(f"[DEBUG] {i}. {hero}: rating={rating:.2f}")

    return hero_scores


# Настраиваемую переменная для бонуса синергии
SYNERGY_BONUS = 0.0

def select_optimal_team(sorted_heroes, hero_roles):
    """
    Выбирает оптимальную команду из 6 героев с учетом ограничений на роль.

    Args:
        sorted_heroes (list): Список героев отсортированный по рейтингу [(hero, score), ...]
        hero_roles (dict): Роли героев {role: [hero1, hero2, ...]}

    Returns:
        list: Список выбранных героев в оптимальном составе
    """
    # Разделяем героев по ролям с маппингом на новый формат
    role_mapping = {
        "Vanguard": "tank",  # Старый формат: tank соответствует Vanguard
        "Duelist": "dd",     # dd соответствует Duelist
        "Strategist": "support"  # support соответствует Strategist
    }

    # Конвертируем роли в старый формат для совместимости
    compatible_hero_roles = {}
    for role, heroes_in_role in hero_roles.items():
        # Используем маппинг на старый формат если возможно
        old_role = role_mapping.get(role, role.lower())
        compatible_hero_roles[old_role] = heroes_in_role

    # Разделяем героев по ролям в старом формате
    vanguards = []  # Авангарды (tank)
    strategists = []  # Стратеги (support)
    duelists = []  # Дуэлянты (dd)

    for hero_name, diff in sorted_heroes:
        role = "unknown"
        for heroes_list in compatible_hero_roles.values():
            if hero_name in heroes_list:
                # Определяем роль из списка
                for role_key, role_heroes in compatible_hero_roles.items():
                    if hero_name in role_heroes:
                        role = role_key
                        break
                break

        if role == "tank":
            vanguards.append((hero_name, diff))
        elif role == "support":
            strategists.append((hero_name, diff))
        elif role == "dd":
            duelists.append((hero_name, diff))

    # Сортируем каждую группу по убыванию difference
    vanguards.sort(key=lambda x: x[1], reverse=True)
    strategists.sort(key=lambda x: x[1], reverse=True)
    duelists.sort(key=lambda x: x[1], reverse=True)

    # Возможные комбинации ролей, удовлетворяющие условиям:
    # V, S, D где V >= 1, 2 <= S <= 3, V + S + D = 6
    possible_combinations = []

    for v in range(1, 5):  # Авангардов может быть от 1 до 4
        for s in range(2, 4):  # Стратегов может быть 2 или 3
            d = 6 - v - s
            if d >= 0:
                possible_combinations.append((v, s, d))

    best_team = None
    best_score = float('-inf')

    # Проверяем каждую возможную комбинацию
    for v_count, s_count, d_count in possible_combinations:
        # Проверяем, достаточно ли героев каждой роли
        if len(vanguards) >= v_count and len(strategists) >= s_count and len(duelists) >= d_count:
            # Формируем команду
            team_candidates = vanguards[:v_count] + strategists[:s_count] + duelists[:d_count]
            team_names = [hero_name[0] for hero_name in team_candidates]

            # Рассчитываем базовый score для команды
            base_score = sum(diff for _, diff in team_candidates)

            # Добавляем синергию - проверяем композиции
            synergy_score = 0
            for i, (hero_name, _) in enumerate(team_candidates):
                for teammate in team_names[i + 1:]:  # Проверяем только идущие после текущего
                    if teammate in compositions_data.get(hero_name, []):
                        synergy_score += SYNERGY_BONUS
                    # Также проверяем обратную синергию
                    if hero_name in compositions_data.get(teammate, []):
                        synergy_score += SYNERGY_BONUS

            # Итоговый score = базовый + синергия
            total_score = base_score + synergy_score

            if total_score > best_score:
                best_score = total_score
                best_team = team_candidates

    # Если не найдено подходящей команды, составляем вручную
    if best_team is None:
        team = []

        # Добавляем как минимум 1 авангарда (лучший)
        if vanguards:
            team.append(vanguards[0])

        # Добавляем как минимум 2 стратега (лучших)
        team.extend(strategists[:min(2, len(strategists))])

        # Добавляем остальных героев
        remaining = []
        remaining.extend(vanguards[1:])  # Оставшиеся авангарды
        remaining.extend(strategists[min(2, len(strategists)):3])  # Может добавить 1 стратега
        remaining.extend(duelists)  # Все дуэлянты

        # Сортируем оставшихся по убыванию difference
        remaining.sort(key=lambda x: x[1], reverse=True)

        # Добавляем героев до 6 человек
        while len(team) < 6 and remaining:
            team.append(remaining.pop(0))

        best_team = team

    # Возвращаем только имена героев
    return [hero[0] for hero in best_team[:6]]


def absolute_with_context(scores, hero_stats):
    """
    Использует абсолютные значения с учётом контекста общей силы героя.

    Args:
        scores (list): Список [(hero, rating), ...]
        hero_stats (dict): Статистика героев

    Returns:
        list: Список [(hero, absolute_score), ...]
    """
    absolute_scores = []

    print("[DEBUG] absolute_with_context: Starting with input scores (first 5):")
    for hero, score in scores[:5]:
        print(f"  {hero}: input_score={score:.2f}")

    for hero, score in scores:
        # Получаем статистику героя
        if hero in hero_stats:
            overall_winrate = hero_stats[hero]["win_rate"] * 100  # Преобразуем back в проценты как в тест
        else:
            overall_winrate = 50.0

        # Чем сильнее герой в целом, тем ценнее его положительный вклад
        context_factor = overall_winrate / 50.0

        # Инвертируем отрицательный score и применяем контекстный фактор
        absolute_score = (100 + score) * context_factor
        absolute_scores.append((hero, absolute_score))

        # Логируем топ-героев
        if score > 2.0:  # Для героев с хорошим рейтингом
            print(f"[DEBUG] {hero}: score={score:.2f}, winrate={overall_winrate:.1f}%, context_factor={context_factor:.3f}, absolute_score={absolute_score:.2f}")

    absolute_scores.sort(key=lambda x: x[1], reverse=True)
    print(f"[DEBUG] absolute_with_context: Final top 10:")
    for i, (hero, absolute_score) in enumerate(absolute_scores[:10], 1):
        print(f"[DEBUG] {i}. {hero}: {absolute_score:.2f}")

    return absolute_scores


# Загружаем данные при импорте модуля
print("Инициализация новой базы данных...")
matchups_data = load_matchups_data()
hero_stats_data = load_hero_stats()
matchups_data = convert_hero_names_opponents(matchups_data)

# Создаем список героев из данных
heroes = list(matchups_data.keys())
print(f"Найдено {len(heroes)} героев")

# Загружаем роли героев для совместимости
# Преобразуем роли в старый формат
roles_data = None
try:
    with open("database/roles.json", 'r', encoding='utf-8') as f:
        roles_raw = json.load(f)
        roles_data = {}
        # Преобразуем роли в старый формат
        role_mapping = {
            "Vanguard": "tanks",
            "Duelist": "attackers",
            "Strategist": "supports"
        }
        for role, heroes_list in roles_raw.items():
            old_role = role_mapping.get(role, role.lower())
            roles_data[old_role] = heroes_list
except FileNotFoundError:
    print("Файл roles.json не найден, используем базовые роли")
    roles_data = {
        "tanks": ["Hulk", "Thor", "The Thing"],
        "supports": ["Groot", "Doctor Strange"],
        "attackers": ["Iron Man", "Captain America"]
    }

# Загружаем синергии героев из JSON файла
compositions_data = load_compositions_data()

# Создаем heroes_compositions в старом формате для совместимости
heroes_compositions = compositions_data

# Создаем heroes_counters для совместимости (старый формат)
heroes_counters = {}
for hero_name, hero_data in matchups_data.items():
    heroes_counters[hero_name] = {}

print("Новая база данных инициализирована")