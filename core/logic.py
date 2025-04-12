# File: logic.py
from collections import deque # Используем deque для selected_heroes
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
from translations import get_text
# Убираем импорты display, т.к. логика не должна отвечать за отображение
# from display import generate_counterpick_display, generate_minimal_display, generate_minimal_icon_list

MIN_TANKS = 1
MAX_TANKS = 3
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self):
        # Используем deque для эффективного добавления/удаления с обоих концов
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set() # Используем set для быстрого поиска
        self.effective_team = []
        # Убрали current_result_text, т.к. текст генерируется в GUI

    def set_selection(self, desired_selection_set):
        """
        Устанавливает выбранных героев в соответствии с переданным множеством.
        Обрабатывает лимит TEAM_SIZE, сохраняя порядок добавления новых
        и удаляя самых старых при переполнении.
        """
        print(f"Logic set_selection called with: {desired_selection_set}")
        print(f"Current selection (before): {list(self.selected_heroes)}")

        current_selection_set = set(self.selected_heroes)
        newly_selected = desired_selection_set - current_selection_set
        deselected = current_selection_set - desired_selection_set

        print(f"Newly selected: {newly_selected}")
        print(f"Deselected: {deselected}")

        # Удаляем тех, кого сняли выделение
        heroes_to_remove_from_deque = []
        for hero in deselected:
            heroes_to_remove_from_deque.append(hero)
            # Снимаем приоритет при снятии выделения
            if hero in self.priority_heroes:
                self.priority_heroes.discard(hero)
                print(f"Priority removed from deselected hero: {hero}")

        # Создаем новый deque без удаленных героев
        if heroes_to_remove_from_deque:
            new_deque = deque([h for h in self.selected_heroes if h not in heroes_to_remove_from_deque], maxlen=TEAM_SIZE)
            self.selected_heroes = new_deque
            print(f"Selection after removal: {list(self.selected_heroes)}")


        # Добавляем новых героев, deque сам обработает maxlen, удаляя старых слева
        for hero in newly_selected:
             # Проверка, если вдруг герой уже там (не должно быть из-за set logic, но на всякий случай)
             if hero not in self.selected_heroes:
                 self.selected_heroes.append(hero) # Добавляем в конец (справа)
                 print(f"Hero appended: {hero}. Current deque: {list(self.selected_heroes)}")


        # Обновляем приоритеты: оставляем только тех, кто все еще выбран
        self.priority_heroes.intersection_update(set(self.selected_heroes))
        print(f"Final selection: {list(self.selected_heroes)}")
        print(f"Final priority: {self.priority_heroes}")

        # Сбрасываем эффективную команду, т.к. выбор изменился
        self.effective_team = []


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
        print("--- Logic: Calculating effective team ---")
        # Исключаем уже выбранных врагов из кандидатов
        candidates = {
            hero: score for hero, score in counter_scores.items()
            if score > 0 and hero not in self.selected_heroes # Основной фильтр
        }

        if not candidates:
            self.effective_team = []
            print("Logic: No positive candidates found after filtering selected heroes.")
            return []

        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        # print(f"Logic: Candidates (Rating > 0, Not Selected): {len(sorted_candidates)}")

        effective_team = deque(maxlen=TEAM_SIZE) # Используем deque для команды
        added_heroes_set = set()
        tanks_count, supports_count, attackers_count = 0, 0, 0

        # Шаг 1: Минимальные требования по ролям (танки и саппорты)
        # Сортируем кандидатов с приоритетом для ролей
        def role_priority_key(item):
            hero, score = item
            if hero in hero_roles.get("tanks", []): return (0, -score)
            if hero in hero_roles.get("supports", []): return (1, -score)
            return (2, -score)
        role_sorted_candidates = sorted(candidates.items(), key=role_priority_key)

        # Заполняем танка(ми)
        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1
        # Заполняем саппорта(ми)
        for hero, score in role_sorted_candidates:
             if supports_count < MIN_SUPPORTS and hero in hero_roles.get("supports", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1

        # print(f"Logic: After initial roles: Team={list(effective_team)}, Tanks={tanks_count}, Supports={supports_count}")

        # Шаг 2: Добор до полной команды с учетом рейтинга, синергии и ограничений
        remaining_candidates = [(h, s) for h, s in sorted_candidates if h not in added_heroes_set]
        # print(f"Logic: Remaining candidates for fill: {len(remaining_candidates)}")

        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1

            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = "unknown"
                 if hero in hero_roles.get("tanks", []): role = "tanks"
                 elif hero in hero_roles.get("supports", []): role = "supports"
                 elif hero in hero_roles.get("attackers", []): role = "attackers"

                 # Проверка ограничений
                 if role == "tanks" and tanks_count < MAX_TANKS: can_add = True
                 elif role == "supports" and supports_count < MAX_SUPPORTS: can_add = True
                 elif role == "attackers": can_add = True
                 elif role == "unknown": can_add = True # Разрешаем неизвестных

                 if can_add:
                     # Расчет синергии с уже добавленными
                     synergy_bonus = 0
                     for teammate in effective_team:
                         if hero in heroes_compositions.get(teammate, []): synergy_bonus += 0.5
                         if teammate in heroes_compositions.get(hero, []): synergy_bonus += 0.5
                     adjusted_score = score + synergy_bonus

                     if adjusted_score > best_adjusted_score:
                         best_adjusted_score = adjusted_score
                         best_hero_to_add = hero
                         candidate_index_to_remove = i

            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add)
                added_heroes_set.add(best_hero_to_add)
                # Обновляем счетчики ролей
                role = "unknown"
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1; role = "tanks"
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1; role = "supports"
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1; role = "attackers"
                # print(f"  -> Added: {best_hero_to_add} (Score: {best_adjusted_score:.1f}, Role: {role})")

                if candidate_index_to_remove != -1:
                    remaining_candidates.pop(candidate_index_to_remove)
            else:
                # print("Logic: No suitable candidates found in this fill iteration.")
                break # Некого больше добавлять

        self.effective_team = list(effective_team) # Сохраняем как список
        print(f"Logic: Final effective team ({len(self.effective_team)}): {self.effective_team}")
        print(f"Logic: Roles: T={tanks_count}, S={supports_count}, A={attackers_count}")
        print("--- Logic: End calculating effective team ---")
        return self.effective_team

# Убираем привязку методов display, они больше не нужны в логике
# CounterpickLogic.generate_counterpick_display = generate_counterpick_display
# CounterpickLogic.generate_minimal_display = generate_minimal_display
# CounterpickLogic.generate_minimal_icon_list = generate_minimal_icon_list