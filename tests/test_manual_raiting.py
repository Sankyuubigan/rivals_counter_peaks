import json
import importlib.util
import os
def load_matchups_data(file_path="test/marvel_rivals_stats_20250810-055947.json"):
    """Загружает данные из JSON файла в новом формате"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Преобразуем данные в старый формат для совместимости с существующим кодом
        old_format_data = {}
        for hero_name, hero_stats in data.items():
            old_format_data[hero_name] = hero_stats.get("opponents", [])
            
        return old_format_data
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка при чтении JSON из файла {file_path}")
        return {}
def load_hero_stats(file_path="test/marvel_rivals_stats_20250810-055947.json"):
    """Загружает общую статистику героев из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        hero_stats = {}
        for hero_name, hero_data in data.items():
            hero_stats[hero_name] = {
                "win_rate": hero_data["win_rate"],
                "pick_rate": hero_data["pick_rate"],
                "matches": hero_data["matches"]
            }
            
        return hero_stats
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка при чтении JSON из файла {file_path}")
        return {}
def load_hero_roles_from_file(file_path="database/roles_and_groups.py"):
    """Загружает роли героев из файла database/roles_and_groups.py"""
    
    # Загружаем модуль
    spec = importlib.util.spec_from_file_location("roles_and_groups", file_path)
    roles_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(roles_module)
    
    # Получаем словарь с ролями
    roles_dict = roles_module.hero_roles
    
    # Создаем соответствие между разными именами героев
    name_mapping = {
        "Widow": "Black Widow",
        "Fister": "Iron Fist",
        "Jeff": "Jeff The Land Shark",
    }
    
    # Преобразуем в формат {имя_героя: роль}
    hero_roles = {}
    
    for role, heroes in roles_dict.items():  # Missing ()
    
        # print(role.value)
        for hero in heroes:
            # print(hero)
            # Используем правильное имя, если есть в маппинге
            hero_name = name_mapping.get(hero, hero)
            hero_roles[hero_name] = role
    # print(hero_roles)
    
    
    
    return hero_roles
   
def absolute_with_context(scores, hero_stats):
    """
    Использует абсолютные значения, но учитывает контекст общей силы героя.
    """
    absolute_scores = []
    
    for hero, score in scores:
        # Получаем статистику героя
        if hero in hero_stats:
            overall_winrate = float(hero_stats[hero]["win_rate"].replace('%', ''))
        else:
            overall_winrate = 50.0
        
        # Чем сильнее герой в целом, тем ценнее его положительный вклад
        context_factor = overall_winrate / 50.0
        
        # Инвертируем отрицательный score и применяем контекстный фактор
        # Чем меньше отрицательное значение (тем лучше герой), тем выше итоговый балл
        absolute_score = (100 + score) * context_factor  # 100 + score превратит -8.75 в 91.25
        absolute_scores.append((hero, absolute_score))
    
    return absolute_scores
def select_optimal_team(sorted_heroes, hero_roles):
    """
    Выбирает оптимальную команду из 6 героев с учетом ограничений на роль.
    """
    # Разделяем героев по ролям
    vanguards = []  # Авангарды
    strategists = []  # Стратеги
    duelists = []  # Дуэлянты
    
    for hero, diff in sorted_heroes:
        role = hero_roles.get(hero, "Unknown")
        if role == "tank":
            vanguards.append((hero, diff))
        elif role == "support":
            strategists.append((hero, diff))
        elif role == "dd":
            duelists.append((hero, diff))
    
    # Сортируем каждую группу по убыванию difference
    vanguards.sort(key=lambda x: x[1], reverse=True)
    strategists.sort(key=lambda x: x[1], reverse=True)
    duelists.sort(key=lambda x: x[1], reverse=True)
    
    # Возможные комбинации ролей, удовлетворяющие условиям:
    # (V, S, D) где V >= 1, 2 <= S <= 3, V + S + D = 6
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
            team = vanguards[:v_count] + strategists[:s_count] + duelists[:d_count]
            score = sum(diff for _, diff in team)
            
            if score > best_score:
                best_score = score
                best_team = team
    
    # Если не найдено подходящей команды, составляем вручную с приоритетом условий
    if best_team is None:
        team = []
        
        # Добавляем как минимум 1 авангард (лучший)
        if vanguards:
            team.append(vanguards[0])
        
        # Добавляем как минимум 2 стратега (лучших)
        team.extend(strategists[:min(2, len(strategists))])
        
        # Добавляем остальных героев, учитывая ограничение максимум 3 стратега
        remaining = []
        remaining.extend(vanguards[1:])  # Оставшиеся авангарды
        remaining.extend(strategists[min(2, len(strategists)):3])  # Может добавить 1 стратега, чтобы стало 3
        remaining.extend(duelists)  # Все дуэлянты
        
        # Сортируем оставшихся по убыванию difference
        remaining.sort(key=lambda x: x[1], reverse=True)
        
        # Добавляем героев до 6 человек
        while len(team) < 6 and remaining:
            hero = remaining.pop(0)
            team.append(hero)
    
        best_team = team
    
    # Возвращаем только имена героев
    return [hero[0] for hero in best_team[:6]]
def calculate_team_counters(enemy_team, matchups_data, hero_roles, method="avg", weighting="equal"):
    """
    Рассчитывает рейтинг героев против указанной команды врагов.
    """
    # Проверяем корректность входных данных
    if not enemy_team:
        raise ValueError("Список вражеских героев не может быть пустым")
    if len(enemy_team) > 6:
        raise ValueError("Максимальное количество вражеских героев - 6")
    if method not in ['sum', 'avg']:
        raise ValueError("Метод агрегации должен быть 'sum' или 'avg'")
    if weighting not in ['equal', 'matches']:
        raise ValueError("Метод взвешивания должно быть 'equal' или 'matches'")
    
    hero_scores = []
    
    # Проходим по каждому герою в базе данных
    for hero, matchups in matchups_data.items():
        total_weighted_difference = 0
        total_weight = 0
        found_matchups = 0
        
        # Проходим по каждому вражескому герою
        for enemy in enemy_team:
            # Ищем матчап против этого врага
            for matchup in matchups:
                # Сравниваем имена, игнорируя регистр и возможные различия в написании
                if matchup["opponent"].lower() == enemy.lower():
                    # Преобразуем строку difference в число
                    diff_str = matchup["difference"].replace('%', '').strip()
                    try:
                        difference = -float(diff_str)
                    except ValueError:
                        continue
                    
                    # Определяем вес
                    weight = 1
                    if weighting == "matches" and "matches" in matchup:
                        # Убираем запятые из числа матчей и преобразуем в int
                        try:
                            matches = int(matchup["matches"].replace(',', ''))
                            weight = matches
                        except ValueError:
                            pass
                    
                    total_weighted_difference += difference * weight
                    total_weight += weight
                    found_matchups += 1
                    break
        
        # Пропускаем героев без данных
        if found_matchups == 0:
            continue
            
        # Рассчитываем итоговый рейтинг
        if total_weight > 0:
            if method == "sum":
                # Нормализуем к среднему, чтобы сравнение было справедливым
                rating = total_weighted_difference / total_weight * len(enemy_team)
            else:  # avg
                rating = total_weighted_difference / total_weight
        else:
            rating = 0
            
        hero_scores.append((hero, rating))
    
    # Сортируем по рейтингу в порядке убывания
    hero_scores.sort(key=lambda x: x[1], reverse=True)
    
    return hero_scores
# Пример использования
if __name__ == "__main__":
    # Загружаем данные
    matchups_data = load_matchups_data()
    hero_stats = load_hero_stats()
    hero_roles = load_hero_roles_from_file()
    
    if matchups_data and hero_stats and hero_roles:
        print("=" * 50)
        enemy_team = ["Hela"]
        num_count=10
        print(f"Поиск оптимальной команды против {enemy_team}")
        hero_scores = calculate_team_counters(enemy_team, matchups_data, hero_roles)
        
        # Рассчитываем абсолютные значения для всех героев
        absolute_scores = absolute_with_context(hero_scores, hero_stats)
        
        # Сортируем по абсолютным значениям
        absolute_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nТоп-10 героев против {enemy_team[0]}:")
        
        for i, (hero, absolute_score) in enumerate(absolute_scores[:num_count], 1):
            role = hero_roles.get(hero, "Unknown")
            print(f"{i}. {hero} ({role}): {absolute_score:.2f}")
        
        # Выбираем оптимальную команду на основе абсолютных значений
        optimal_team = select_optimal_team(absolute_scores, hero_roles)
        print(f"\nОптимальная команда из 6 героев против {enemy_team[0]}:")
        
        for i, hero in enumerate(optimal_team, 1):
            role = hero_roles.get(hero, "Unknown")
            # Находим абсолютное значение для отображения
            absolute_score = next((score for h, score in absolute_scores if h == hero), 0)
            print(f"{i}. {hero} ({role}): {absolute_score:.2f}")
        
        # Проверяем условия
        vanguard_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "tank")
        strategist_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "support")
        duelist_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "dd")
        
        print(f"\nПроверка условий:")
        print(f"- Авангардов: {vanguard_count} (должно быть >= 1)")
        print(f"- Стратегов: {strategist_count} (должно быть 2-3)")
        print(f"- Дуэлянтов: {duelist_count} (остальные)")