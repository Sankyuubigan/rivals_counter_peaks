import json

def load_matchups_data(file_path):
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

def load_hero_stats(file_path):
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

def load_hero_roles_from_file(file_path="database/roles.json"):
    """Загружает роли героев из файла database/roles.json"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Преобразуем в формат {имя_героя: роль}
        hero_roles = {}
        for role, heroes in data.items():
            for hero in heroes:
                hero_roles[hero] = role
        return hero_roles
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка при чтении JSON из файла {file_path}")
        return {}

def absolute_with_context(scores, hero_stats):
    """
    Использует абсолютные значения, но учитывает контекст общей силы героя.
    Нормализует результаты для отображения в диапазоне 1-100, сохраняя исходный порядок.
    """
    # Шаг 1: Рассчитываем баллы по исходной формуле
    original_scores = []
    
    for hero, score in scores:
        # Получаем статистику героя
        if hero in hero_stats:
            overall_winrate = float(hero_stats[hero]["win_rate"].replace('%', ''))
        else:
            overall_winrate = 50.0
        
        # Чем сильнее герой в целом, тем ценнее его положительный вклад
        context_factor = overall_winrate / 50.0
        
        # ИСПОЛЬЗУЕМ ИСХОДНУЮ ФОРМУЛУ
        absolute_score = (100 + score) * context_factor  # 100 + score превратит -8.75 в 91.25
        original_scores.append((hero, absolute_score))
    
    # Шаг 2: Находим минимальный и максимальный баллы для нормализации отображения
    if not original_scores:
        return []
    
    original_values = [score for _, score in original_scores]
    min_score = min(original_values)
    max_score = max(original_values)
    
    # Шаг 3: Нормализуем ТОЛЬКО для отображения в диапазоне 1-100, сохраняя исходный порядок
    display_scores = []
    
    # Если все баллы одинаковы, избегаем деления на ноль
    if max_score == min_score:
        # Всем присваиваем 50.5 (середина диапазона 1-100)
        for hero, _ in original_scores:
            display_scores.append((hero, 50.5))
    else:
        for hero, original_score in original_scores:
            # Нормализация в диапазоне 1-100: (x - min) / (max - min) * 99 + 1
            display_score = (original_score - min_score) / (max_score - min_score) * 99 + 1
            display_scores.append((hero, display_score))
    
    return display_scores

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
        if role == "Vanguard":
            vanguards.append((hero, diff))
        elif role == "Strategist":
            strategists.append((hero, diff))
        elif role == "Duelist":
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
    file_database="database/marvel_rivals_stats_20251017-202023.json"
    # Загружаем данные
    matchups_data = load_matchups_data(file_database)
    hero_stats = load_hero_stats(file_database)
    hero_roles = load_hero_roles_from_file()
    
    if matchups_data and hero_stats and hero_roles:
        print("=" * 50)
        enemy_team = [
        "Peni Parker"
        ]
        num_count = 40
        print(f"Поиск оптимальной команды против {len(enemy_team)} врагов")
        
        hero_scores = calculate_team_counters(enemy_team, matchups_data, hero_roles)
        
        # Рассчитываем абсолютные значения для всех героев (с нормализацией для отображения)
        absolute_scores = absolute_with_context(hero_scores, hero_stats)
        
        # Сортируем по абсолютным значениям (сохраняем исходный порядок)
        absolute_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nТоп-{num_count} героев против команды врагов:")
        
        for i, (hero, absolute_score) in enumerate(absolute_scores[:num_count], 1):
            role = hero_roles.get(hero, "Unknown")
            print(f"{i:2d}. {hero:<20} ({role:<11}): {absolute_score:6.2f}")
        
        # Выбираем оптимальную команду на основе абсолютных значений
        optimal_team = select_optimal_team(absolute_scores, hero_roles)
        print(f"\nОптимальная команда из 6 героев:")
        
        for i, hero in enumerate(optimal_team, 1):
            role = hero_roles.get(hero, "Unknown")
            # Находим абсолютное значение для отображения
            absolute_score = next((score for h, score in absolute_scores if h == hero), 0)
            print(f"{i}. {hero} ({role}): {absolute_score:.2f}")
        
        # Проверяем условия
        vanguard_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "Vanguard")
        strategist_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "Strategist")
        duelist_count = sum(1 for hero in optimal_team if hero_roles.get(hero) == "Duelist")
        
        print(f"\nПроверка условий:")
        print(f"- Авангардов: {vanguard_count} (должно быть >= 1)")
        print(f"- Стратегов: {strategist_count} (должно быть 2-3)")
        print(f"- Дуэлянтов: {duelist_count} (остальные)")
        print(f"- Всего: {vanguard_count + strategist_count + duelist_count} героев")
        
        # ====== НОВЫЙ УЛУЧШЕННЫЙ СПИСОК ======
        print(f"\n{'='*50}")
        print("УЛУЧШЕННЫЙ СПИСОК (оптимальная команда + остальные по баллам):")
        
        # Создаем улучшенный список
        improved_list = []
        
        # 1. Добавляем оптимальную команду (первые 6 героев)
        for hero in optimal_team:
            absolute_score = next((score for h, score in absolute_scores if h == hero), 0)
            improved_list.append((hero, absolute_score))
        
        # 2. Добавляем оставшихся героев (начиная с 7-го места), отсортированных по баллам
        # Создаем множество имен героев из оптимальной команды для быстрой проверки
        optimal_team_set = set(optimal_team)
        
        # Фильтруем normalized_scores, исключая героев из оптимальной команды
        remaining_heroes = [(hero, score) for hero, score in absolute_scores if hero not in optimal_team_set]
        
        # Добавляем оставшихся героев в улучшенный список
        improved_list.extend(remaining_heroes)
        
        # Выводим улучшенный список (ограничиваем первыми 41 позициями)
        print(f"\nТоп-41 героев (улучшенный список):")
        for i, (hero, absolute_score) in enumerate(improved_list[:41], 1):
            role = hero_roles.get(hero, "Unknown")
            # Для первых 6 героев добавляем пометку "ОПТИМАЛЬНАЯ КОМАНДА"
            if i <= 6:
                print(f"{i:2d}. {hero:<20} ({role:<11}): {absolute_score:6.2f} [ОПТИМАЛЬНАЯ КОМАНДА]")
            else:
                print(f"{i:2d}. {hero:<20} ({role:<11}): {absolute_score:6.2f}")