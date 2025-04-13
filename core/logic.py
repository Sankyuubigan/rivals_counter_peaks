# File: logic.py
from collections import deque # Используем deque для selected_heroes
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
from translations import get_text

MIN_TANKS = 1
MAX_TANKS = 3
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self):
        # Используем deque для эффективного добавления/удаления с обоих концов
        # maxlen сам будет удалять старые элементы при переполнении
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set() # Используем set для быстрого поиска
        self.effective_team = []

    # --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ---
    def set_selection(self, desired_ui_selection_set):
        """
        Обновляет внутренний список выбранных героев (deque),
        чтобы он соответствовал переданному множеству из UI.
        Сохраняет порядок добавления новых и учитывает TEAM_SIZE.
        """
        print(f"Logic set_selection called with UI selection: {desired_ui_selection_set}")
        print(f"Current internal selection (before): {list(self.selected_heroes)}")

        # Создаем новый deque на основе текущего состояния UI, сохраняя порядок старых
        new_deque = deque(maxlen=TEAM_SIZE)
        heroes_added_from_desired = set()

        # 1. Добавляем существующих героев из старого deque, если они есть в новом наборе от UI
        for hero in list(self.selected_heroes): # Итерируемся по копии старого deque
            if hero in desired_ui_selection_set:
                new_deque.append(hero)
                heroes_added_from_desired.add(hero)

        # 2. Добавляем новых героев (которые есть в UI, но не были в старом deque) в конец
        for hero in desired_ui_selection_set:
             if hero not in heroes_added_from_desired:
                 new_deque.append(hero) # deque сам обработает maxlen

        # 3. Обновляем основной deque
        self.selected_heroes = new_deque

        # 4. Обновляем приоритеты: оставляем только тех, кто все еще выбран
        self.priority_heroes.intersection_update(set(self.selected_heroes))

        print(f"Final internal selection: {list(self.selected_heroes)}")
        print(f"Final priority: {self.priority_heroes}")

        # Сбрасываем эффективную команду, т.к. выбор изменился
        self.effective_team = []
    # --- КОНЕЦ ИСПРАВЛЕННОЙ ФУНКЦИИ ---


    def clear_all(self):
        """Очищает все выборы и приоритеты."""
        print("Logic: Clearing all selections.")
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team = []


    def set_priority(self, hero):
        """Устанавливает или снимает приоритет героя."""
        if hero not in self.selected_heroes:
            print(f"Logic: Cannot set priority for non-selected hero: {hero}")
            return

        if hero in self.priority_heroes:
            self.priority_heroes.discard(hero) # Используем discard для set
            print(f"Logic: Priority removed from {hero}")
        else:
            self.priority_heroes.add(hero) # Используем add для set
            print(f"Logic: Priority set for {hero}")
        # Сбрасываем эффективную команду, т.к. приоритеты влияют на расчет
        self.effective_team = []


    def get_selected_heroes_text(self):
        """Возвращает текст для метки 'Выбрано: ...'."""
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes) # Преобразуем deque в список для join
        if not heroes_list:
            return get_text('selected') # "Выбрано"
        else:
            header = f"{get_text('selected')} ({count}/{TEAM_SIZE}): "
            return f"{header}{', '.join(heroes_list)}"

    def calculate_counter_scores(self):
        """Рассчитывает рейтинг контрпиков."""
        counter_scores = {hero: 0.0 for hero in heroes}
        current_selection_set = set(self.selected_heroes) # Для быстрой проверки

        # Шаг 1: Начисляем очки за контру выбранных врагов
        for selected_enemy in self.selected_heroes:
            for counter_pick in heroes_counters.get(selected_enemy, []):
                if counter_pick in counter_scores:
                    score_increase = 2.0 if selected_enemy in self.priority_heroes else 1.0
                    counter_scores[counter_pick] += score_increase

        # Шаг 2: Применяем штрафы
        for potential_pick in heroes:
            if potential_pick not in counter_scores: continue

            # Штраф, если потенциальный пик выбран врагом
            if potential_pick in current_selection_set:
                counter_scores[potential_pick] -= 5.0 # Большой штраф за выбор врага

            # Штраф за каждого врага, который контрит потенциальный пик
            counters_for_potential_pick = heroes_counters.get(potential_pick, [])
            for selected_enemy in self.selected_heroes:
                if selected_enemy in counters_for_potential_pick:
                    score_decrease = 1.5 if selected_enemy in self.priority_heroes else 1.0
                    counter_scores[potential_pick] -= score_decrease

        return counter_scores


    def calculate_effective_team(self, counter_scores):
        """Рассчитывает рекомендуемую команду."""
        # print("--- Logic: Calculating effective team ---")
        candidates = {
            hero: score for hero, score in counter_scores.items()
            if score > 0 and hero not in self.selected_heroes
        }

        if not candidates:
            self.effective_team = []
            # print("Logic: No positive candidates found after filtering selected heroes.")
            return []

        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        effective_team = deque(maxlen=TEAM_SIZE)
        added_heroes_set = set()
        tanks_count, supports_count, attackers_count = 0, 0, 0

        # Шаг 1: Минимальные требования по ролям
        def role_priority_key(item):
            hero, score = item
            if hero in hero_roles.get("tanks", []): return (0, -score)
            if hero in hero_roles.get("supports", []): return (1, -score)
            return (2, -score)
        role_sorted_candidates = sorted(candidates.items(), key=role_priority_key)

        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1
        for hero, score in role_sorted_candidates:
             if supports_count < MIN_SUPPORTS and hero in hero_roles.get("supports", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1

        # Шаг 2: Добор до полной команды
        remaining_candidates = [(h, s) for h, s in sorted_candidates if h not in added_heroes_set]
        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1
            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = "unknown"
                 if hero in hero_roles.get("tanks", []): role = "tanks"
                 elif hero in hero_roles.get("supports", []): role = "supports"
                 elif hero in hero_roles.get("attackers", []): role = "attackers"

                 if role == "tanks" and tanks_count < MAX_TANKS: can_add = True
                 elif role == "supports" and supports_count < MAX_SUPPORTS: can_add = True
                 elif role == "attackers": can_add = True
                 elif role == "unknown": can_add = True

                 if can_add:
                     synergy_bonus = 0
                     for teammate in effective_team:
                         if hero in heroes_compositions.get(teammate, []): synergy_bonus += 0.5
                         if teammate in heroes_compositions.get(hero, []): synergy_bonus += 0.5
                     adjusted_score = score + synergy_bonus
                     if adjusted_score > best_adjusted_score:
                         best_adjusted_score = adjusted_score; best_hero_to_add = hero; candidate_index_to_remove = i

            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add)
                added_heroes_set.add(best_hero_to_add)
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1
                if candidate_index_to_remove != -1: remaining_candidates.pop(candidate_index_to_remove)
            else: break

        self.effective_team = list(effective_team)
        # print(f"Logic: Final effective team ({len(self.effective_team)}): {self.effective_team}")
        # print(f"Logic: Roles: T={tanks_count}, S={supports_count}, A={attackers_count}")
        # print("--- Logic: End calculating effective team ---")
        return self.effective_team