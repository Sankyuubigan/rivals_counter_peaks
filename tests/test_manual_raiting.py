import json

# --- ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ ---

def load_matchups_data(file_path):
    """Загружает данные о противниках из JSON файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_format_data = {}
        heroes_data = data.get("heroes", {})
        for hero_name, hero_stats in heroes_data.items():
            if isinstance(hero_stats, dict):
                opponents = hero_stats.get("opponents", [])
                old_format_data[hero_name] = opponents
        return old_format_data
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке данных из {file_path}: {e}")
        return {}

def load_hero_stats(file_path):
    """Загружает общую статистику героев из JSON файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        hero_stats = {}
        heroes_data = data.get("heroes", {})
        for hero_name, hero_data in heroes_data.items():
            if isinstance(hero_data, dict):
                try:
                    hero_stats[hero_name] = {
                        "win_rate": hero_data["win_rate"],
                        "pick_rate": hero_data["pick_rate"],
                        "matches": hero_data["matches"]
                    }
                except KeyError: continue
        return hero_stats
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке данных из {file_path}: {e}")
        return {}

def load_hero_roles_from_file(file_path="database/roles.json"):
    """Загружает роли героев из файла database/roles.json."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
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

def load_teamups_data(file_path):
    """Загружает и обрабатывает данные о тимапах из основного файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        teamups_data = {}
        teamups_list = data.get("teamups", [])
        for teamup in teamups_list:
            heroes_set = frozenset(teamup["heroes"])
            teamups_data[heroes_set] = teamup
        return teamups_data
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке тимапов из {file_path}: {e}")
        return {}

def load_full_data_for_maps(file_path):
    """Загружает полный JSON, чтобы получить доступ к данным по картам."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Не удалось загрузить полные данные для карт: {e}")
        return None

# --- ФУНКЦИИ РАСЧЕТА ---

def get_map_score(full_data, hero_name, map_name, min_score=0, max_score=20):
    """
    Рассчитывает балл для конкретной карты конкретного героя.
    """
    hero_data = full_data.get('heroes', {}).get(hero_name)
    if not hero_data: return 0

    maps_list = hero_data.get('maps', [])
    if not maps_list: return 0

    win_rates = []
    target_map_wr = None
    for map_info in maps_list:
        try:
            wr = float(map_info['win_rate'].replace('%', ''))
            win_rates.append(wr)
            if map_info['map_name'] == map_name:
                target_map_wr = wr
        except (KeyError, ValueError): continue

    if target_map_wr is None: return 0

    min_wr = min(win_rates)
    max_wr = max(win_rates)

    if min_wr == max_wr: return float(min_score)
    
    score = min_score + (target_map_wr - min_wr) * (max_score - min_score) / (max_wr - min_wr)
    return round(score, 2)

def calculate_team_score_with_synergy(team_list, teamups_data, bonus=10):
    """Рассчитывает общую силу команды с учетом бонусов за тимапы."""
    total_score = sum(score for _, score in team_list)
    team_heroes_names = {hero for hero, _ in team_list}
    synergy_bonus = 0
    for teamup_heroes_set in teamups_data.keys():
        if teamup_heroes_set.issubset(team_heroes_names):
            synergy_bonus += bonus
    return total_score + synergy_bonus

def select_optimal_team(sorted_heroes, hero_roles, teamups_data=None):
    """Выбирает оптимальную команду из 6 героев."""
    vanguards, strategists, duelists = [], [], []
    for hero, diff in sorted_heroes:
        role = hero_roles.get(hero, "Unknown")
        if role == "Vanguard": vanguards.append((hero, diff))
        elif role == "Strategist": strategists.append((hero, diff))
        elif role == "Duelist": duelists.append((hero, diff))
    
    vanguards.sort(key=lambda x: x[1], reverse=True)
    strategists.sort(key=lambda x: x[1], reverse=True)
    duelists.sort(key=lambda x: x[1], reverse=True)
    
    best_team, best_score = None, float('-inf')
    for v in range(1, 5):
        for s in range(2, 4):
            d = 6 - v - s
            if d >= 0 and len(vanguards) >= v and len(strategists) >= s and len(duelists) >= d:
                team = vanguards[:v] + strategists[:s] + duelists[:d]
                score = calculate_team_score_with_synergy(team, teamups_data) if teamups_data else sum(diff for _, diff in team)
                if score > best_score:
                    best_score, best_team = score, team
    
    if best_team is None: # Fallback
        team = []
        if vanguards: team.append(vanguards[0])
        team.extend(strategists[:min(2, len(strategists))])
        remaining = sorted(vanguards[1:] + strategists[min(2, len(strategists)):3] + duelists, key=lambda x: x[1], reverse=True)
        while len(team) < 6 and remaining: team.append(remaining.pop(0))
        best_team = team

    return [hero[0] for hero in best_team[:6]]

def absolute_with_context(scores, hero_stats):
    """Рассчитывает абсолютные значения с нормализацией."""
    original_scores = []
    for hero, score in scores:
        if hero in hero_stats:
            overall_winrate = float(hero_stats[hero]["win_rate"].replace('%', ''))
        else: overall_winrate = 50.0
        context_factor = overall_winrate / 50.0
        absolute_score = (100 + score) * context_factor
        original_scores.append((hero, absolute_score))
    
    if not original_scores: return []
    original_values = [score for _, score in original_scores]
    min_score, max_score = min(original_values), max(original_values)
    display_scores = []
    if max_score == min_score:
        for hero, _ in original_scores: display_scores.append((hero, 50.5))
    else:
        for hero, original_score in original_scores:
            display_score = (original_score - min_score) / (max_score - min_score) * 99 + 1
            display_scores.append((hero, display_score))
    return display_scores

def calculate_team_counters(enemy_team, matchups_data, hero_roles, method="avg", weighting="equal"):
    """Рассчитывает рейтинг героев против указанной команды врагов."""
    if not enemy_team: raise ValueError("Список вражеских героев не может быть пустым")
    hero_scores = []
    for hero, matchups in matchups_data.items():
        total_weighted_difference, total_weight, found_matchups = 0, 0, 0
        for enemy in enemy_team:
            for matchup in matchups:
                if matchup["opponent"].lower() == enemy.lower():
                    try:
                        difference = -float(matchup["difference"].replace('%', '').strip())
                        weight = 1
                        if weighting == "matches" and "matches" in matchup:
                            weight = int(matchup["matches"].replace(',', ''))
                        total_weighted_difference += difference * weight
                        total_weight += weight
                        found_matchups += 1
                        break
                    except (ValueError, KeyError): continue
        if found_matchups > 0:
            rating = (total_weighted_difference / total_weight * len(enemy_team)) if method == "sum" else total_weighted_difference / total_weight
            hero_scores.append((hero, rating))
    hero_scores.sort(key=lambda x: x[1], reverse=True)
    return hero_scores

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ВЫВОДА СПИСКА ГЕРОЕВ ---

def log_hero_list(optimal_team, all_heroes_scores, hero_roles, title="Список героев"):
    """
    Выводит в лог дополнительный список героев, где сначала идет оптимальная команда 6 героев,
    а затем все остальные по баллам по убыванию.
    
    Args:
        optimal_team: Список из 6 героев оптимальной команды
        all_heroes_scores: Список всех героев с их баллами [(hero, score), ...]
        hero_roles: Словарь с ролями героев {hero: role}
        title: Заголовок для вывода
    """
    print(f"\n{'='*20} {title} {'='*20}")
    
    # Создаем словарь для быстрого доступа к баллам героев
    scores_dict = {hero: score for hero, score in all_heroes_scores}
    
    # Сначала выводим оптимальную команду
    print("\nОптимальная команда:")
    for i, hero in enumerate(optimal_team, 1):
        role = hero_roles.get(hero, "Unknown")
        score = scores_dict.get(hero, 0)
        print(f"{i}. {hero} ({role}): {score:.2f}")
    
    # Создаем список всех героев, не входящих в оптимальную команду
    other_heroes = [(hero, score) for hero, score in all_heroes_scores if hero not in optimal_team]
    
    # Сортируем остальных героев по баллам по убыванию
    other_heroes.sort(key=lambda x: x[1], reverse=True)
    
    # Выводим остальных героев
    print("\nОстальные герои (по убыванию баллов):")
    for i, (hero, score) in enumerate(other_heroes, 1):
        role = hero_roles.get(hero, "Unknown")
        print(f"{i}. {hero} ({role}): {score:.2f}")

# --- ОСНОВНОЙ БЛОК ВЫПОЛНЕНИЯ ---

if __name__ == "__main__":
    file_database = "database/marvel_rivals_stats_20251017-202023.json"
    
    # Запрашиваем название карты
    map_name = ""

    # Загружаем все необходимые данные
    matchups_data = load_matchups_data(file_database)
    hero_stats = load_hero_stats(file_database)
    hero_roles = load_hero_roles_from_file()
    teamups_data = load_teamups_data(file_database)
    full_data_for_maps = load_full_data_for_maps(file_database) if map_name else None
    
    if not all([matchups_data, hero_stats, hero_roles, teamups_data]):
        print("Не удалось загрузить одну из частей данных. Проверьте файлы.")
    else:
        print("=" * 50)
        enemy_team = ["Spider Man"]
        num_count = 50
        print(f"Поиск оптимальной команды против {len(enemy_team)} врагов: {', '.join(enemy_team)}")
        
        hero_scores = calculate_team_counters(enemy_team, matchups_data, hero_roles)
        absolute_scores = absolute_with_context(hero_scores, hero_stats)
        absolute_scores.sort(key=lambda x: x[1], reverse=True)
        
        # --- ЧАСТЬ 1: РАСЧЕТ БЕЗ УЧЕТА СИНЕРГИЙ ---
        print(f"\n{'='*20} РАСЧЕТ БЕЗ УЧЕТА СИНЕРГИЙ {'='*20}")
        print(f"\nТоп-{num_count} героев против команды врагов:")
        for i, (hero, absolute_score) in enumerate(absolute_scores[:num_count], 1):
            role = hero_roles.get(hero, "Unknown")
            print(f"{i:2d}. {hero:<20} ({role:<11}): {absolute_score:6.2f}")
        
        optimal_team_standard = select_optimal_team(absolute_scores, hero_roles, teamups_data=None)
        print(f"\nОптимальная команда (без синергий):")
        for i, hero in enumerate(optimal_team_standard, 1):
            role = hero_roles.get(hero, "Unknown")
            absolute_score = next((score for h, score in absolute_scores if h == hero), 0)
            print(f"{i}. {hero} ({role}): {absolute_score:.2f}")
        
        # Выводим дополнительный список героев для расчета без синергий
        log_hero_list(optimal_team_standard, absolute_scores, hero_roles, "ПОЛНЫЙ СПИСОК ГЕРОЕВ (БЕЗ СИНЕРГИЙ)")

        # --- ЧАСТЬ 2: РАСЧЕТ С УЧЕТОМ СИНЕРГИЙ ---
        print(f"\n\n{'='*20} РАСЧЕТ С УЧЕТОМ СИНЕРГИЙ {'='*20}")
        optimal_team_synergy = select_optimal_team(absolute_scores, hero_roles, teamups_data=teamups_data)
        print(f"\nОптимальная команда (с учетом синергий):")
        for i, hero in enumerate(optimal_team_synergy, 1):
            role = hero_roles.get(hero, "Unknown")
            absolute_score = next((score for h, score in absolute_scores if h == hero), 0)
            print(f"{i}. {hero} ({role}): {absolute_score:.2f}")
            
        print(f"\nАНАЛИЗ СИНЕРГИЙ:")
        optimal_team_synergy_set = set(optimal_team_synergy)
        found_teamups = []
        try:
            with open(file_database, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for teamup in data.get("teamups", []):
                    if set(teamup["heroes"]).issubset(optimal_team_synergy_set):
                        found_teamups.append(f"{', '.join(teamup['heroes'])} ({teamup['tier']}-тир)")
        except: pass

        if found_teamups:
            for teamup in found_teamups: print(f"  - {teamup}")
        else:
            print("  - Не найдено известных тимапов.")
        
        # Выводим дополнительный список героев для расчета с синергиями
        log_hero_list(optimal_team_synergy, absolute_scores, hero_roles, "ПОЛНЫЙ СПИСОК ГЕРОЕВ (С СИНЕРГИЯМИ)")

        # --- ЧАСТЬ 3: РАСЧЕТ С УЧЕТОМ КАРТЫ ---
        if map_name and full_data_for_maps:
            print(f"\n\n{'='*20} РАСЧЕТ С УЧЕТОМ КАРТЫ: {map_name.upper()} {'='*20}")
            
            map_adjusted_scores = []
            for hero, base_score in absolute_scores:
                map_bonus = get_map_score(full_data_for_maps, hero, map_name)
                final_score = base_score + map_bonus
                map_adjusted_scores.append((hero, final_score, map_bonus))
            
            map_adjusted_scores.sort(key=lambda x: x[1], reverse=True)

            print(f"\nТоп-{num_count} героев с учетом бонуса за карту:")
            for i, (hero, final_score, bonus) in enumerate(map_adjusted_scores[:num_count], 1):
                role = hero_roles.get(hero, "Unknown")
                print(f"{i:2d}. {hero:<20} ({role:<11}): {final_score:6.2f} (+{bonus:.2f})")
            
            optimal_team_map = select_optimal_team([(h, s) for h, s, _ in map_adjusted_scores], hero_roles)
            print(f"\nОптимальная команда (с учетом карты):")
            for i, hero in enumerate(optimal_team_map, 1):
                role = hero_roles.get(hero, "Unknown")
                # Находим итоговый балл для отображения
                final_score_display = next((score for h, score, _ in map_adjusted_scores if h == hero), 0)
                bonus_display = next((bonus for h, _, bonus in map_adjusted_scores if h == hero), 0)
                print(f"{i}. {hero} ({role}): {final_score_display:.2f} (+{bonus_display:.2f})")
            
            # Выводим дополнительный список героев для расчета с учетом карты
            map_scores_only = [(h, s) for h, s, _ in map_adjusted_scores]
            log_hero_list(optimal_team_map, map_scores_only, hero_roles, f"ПОЛНЫЙ СПИСОК ГЕРОЕВ (С УЧЕТОМ КАРТЫ {map_name.upper()})")
        elif map_name:
            print(f"\n\n{'='*20} РАСЧЕТ С УЧЕТОМ КАРТЫ: {map_name.upper()} {'='*20}")
            print(f"Не удалось найти данные для карты '{map_name}' или файл с данными о картах отсутствует.")