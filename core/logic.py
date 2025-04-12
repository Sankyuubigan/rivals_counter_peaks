# File: logic.py
from PySide6.QtWidgets import QLabel
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
from translations import get_text
from display import generate_counterpick_display, generate_minimal_display, generate_minimal_icon_list

MIN_TANKS = 1
MAX_TANKS = 3
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self):
        self.selected_heroes = [] # Список выбранных героев (сохраняет порядок выбора)
        self.priority_heroes = []
        self.current_result_text = ""
        self.effective_team = []

    def toggle_hero(self, hero, update_ui_callback):
        """
        Добавляет или удаляет героя.
        Если лимит (TEAM_SIZE) достигнут при добавлении,
        удаляет самого старого героя (первого в списке) и добавляет нового.
        Вызывает update_ui_callback в конце, если он предоставлен.
        """
        was_selected = hero in self.selected_heroes
        is_adding = not was_selected
        limit_reached = len(self.selected_heroes) >= TEAM_SIZE

        removed_hero_for_replacement = None # Герой, который будет удален при замене

        print(f"toggle_hero called for: {hero}. Is adding: {is_adding}. Limit reached: {limit_reached}")

        if is_adding:
            if limit_reached:
                # --- Логика замены ---
                removed_hero_for_replacement = self.selected_heroes.pop(0) # Удаляем первого (самого старого)
                print(f"Limit reached. Removing oldest hero: {removed_hero_for_replacement} to add {hero}")
                # Если удаленный герой был в приоритете, убираем его оттуда
                if removed_hero_for_replacement in self.priority_heroes:
                    self.priority_heroes.remove(removed_hero_for_replacement)
                    print(f"Priority removed from replaced hero: {removed_hero_for_replacement}")
                # --- Добавляем нового героя ---
                self.selected_heroes.append(hero)
                print(f"New hero added: {hero}")
            else:
                # --- Простое добавление ---
                self.selected_heroes.append(hero)
                print(f"Hero added: {hero}")
        else:
            # --- Удаление героя ---
            if hero in self.selected_heroes:
                 self.selected_heroes.remove(hero)
                 print(f"Hero removed: {hero}")
                 # Если удаленный герой был в приоритете, убираем его оттуда
                 if hero in self.priority_heroes:
                     self.priority_heroes.remove(hero)
                     print(f"Priority removed from deselected hero: {hero}")
            else:
                 print(f"Hero {hero} not found in selection for removal.") # Странная ситуация

        print(f"Current selected_heroes: {self.selected_heroes}")
        print(f"Current priority_heroes: {self.priority_heroes}")

        # Вызываем коллбэк один раз в конце, если он есть
        if update_ui_callback:
            update_ui_callback()

    def clear_all(self, update_ui_callback):
        """Очищает списки и вызывает ОДИН callback."""
        print("Очистка всех выборов.")
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team.clear()
        if update_ui_callback:
            update_ui_callback()

    def set_priority(self, hero, update_ui_callback):
        """Устанавливает или снимает приоритет героя и вызывает ОДИН callback."""
        if hero not in self.selected_heroes:
            print(f"Нельзя установить приоритет для невыбранного героя: {hero}")
            return

        if hero in self.priority_heroes:
            self.priority_heroes.remove(hero)
            print(f"Приоритет снят с {hero}")
        else:
            # Можно добавить ограничение на количество приоритетных, если нужно
            self.priority_heroes.append(hero)
            print(f"Приоритет установлен для {hero}")

        if update_ui_callback:
             update_ui_callback()

    def get_selected_heroes_text(self):
        """Возвращает текст для метки 'Выбрано: ...'."""
        count = len(self.selected_heroes)
        if not self.selected_heroes:
            # Возвращаем только базовый текст, если ничего не выбрано
            return get_text('selected') # "Выбрано: "
        else:
            # Показываем счетчик и список
            header = f"{get_text('selected')} ({count}/{TEAM_SIZE}): "
            # Отображаем всех выбранных героев в порядке выбора
            return f"{header}{', '.join(self.selected_heroes)}"

    def calculate_counter_scores(self):
        counter_scores = {hero: 0.0 for hero in heroes}
        for selected_hero in self.selected_heroes:
            # Добавляем очки тем, кто контрит выбранного героя
            for counter in heroes_counters.get(selected_hero, []):
                if counter in counter_scores:
                    # Приоритетные враги дают больший вклад в рейтинг их контрпиков
                    score_increase = 2.0 if selected_hero in self.priority_heroes else 1.0
                    counter_scores[counter] += score_increase

            # Уменьшаем рейтинг самого выбранного героя (штраф за выбор)
            if selected_hero in counter_scores:
                 counter_scores[selected_hero] -= 1.0

        # Уменьшаем рейтинг героя за каждого выбранного врага, который его контрит
        for potential_pick in heroes: # Итерируем по всем возможным нашим пикам
             if potential_pick not in counter_scores: continue # Пропускаем, если героя нет в базе
             counters_for_potential_pick = heroes_counters.get(potential_pick, []) # Кто контрит наш возможный пик
             for selected_enemy in self.selected_heroes: # Проверяем против каждого выбранного врага
                 if selected_enemy in counters_for_potential_pick: # Если враг контрит наш пик
                     # Приоритетные враги сильнее снижают рейтинг тех, кого они контрят
                     score_decrease = 1.5 if selected_enemy in self.priority_heroes else 1.0
                     counter_scores[potential_pick] -= score_decrease

        return counter_scores


    def calculate_effective_team(self, counter_scores):
        # ... (код без изменений) ...
        print("--- Расчет эффективной команды ---")
        positive_counters = {hero: score for hero, score in counter_scores.items() if score > 0}
        if not positive_counters:
            self.effective_team = []
            print("Нет героев с положительным рейтингом для формирования команды.")
            return []
        sorted_counters = sorted(positive_counters.items(), key=lambda x: x[1], reverse=True)
        print(f"Кандидаты (рейтинг > 0): {len(sorted_counters)}")
        effective_team = []
        tanks_count = 0
        supports_count = 0
        attackers_count = 0
        added_heroes_set = set()
        # Шаг 1: Минимальные требования
        heroes_added_in_step = 0
        def role_priority_key(item):
            hero, score = item
            if hero in hero_roles.get("tanks", []): return (0, -score) # Танки первыми
            if hero in hero_roles.get("supports", []): return (1, -score) # Саппорты вторыми
            return (2, -score) # Остальные
        role_sorted_candidates = sorted(positive_counters.items(), key=role_priority_key)
        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1; heroes_added_in_step += 1
        print(f"Добавлено {heroes_added_in_step} танков на шаге 1 (мин {MIN_TANKS}). Текущая команда: {effective_team}")
        heroes_added_in_step = 0
        for hero, score in role_sorted_candidates:
             if supports_count < MIN_SUPPORTS and hero in hero_roles.get("supports", []) and hero not in added_heroes_set:
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1; heroes_added_in_step += 1
        print(f"Добавлено {heroes_added_in_step} саппортов на шаге 1 (мин {MIN_SUPPORTS}). Текущая команда: {effective_team}")
        # Шаг 2: Добор до полной команды
        remaining_candidates = [(h, s) for h, s in sorted_counters if h not in added_heroes_set]
        print(f"Осталось кандидатов для добора: {len(remaining_candidates)}")
        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1
            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = None
                 if hero in hero_roles.get("tanks", []): role = "tanks"
                 elif hero in hero_roles.get("supports", []): role = "supports"
                 elif hero in hero_roles.get("attackers", []): role = "attackers"
                 else: role = "unknown"
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
                         best_adjusted_score = adjusted_score
                         best_hero_to_add = hero
                         candidate_index_to_remove = i
            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add)
                added_heroes_set.add(best_hero_to_add)
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1
                print(f"  -> Добавлен: {best_hero_to_add} (adj_score: {best_adjusted_score:.1f}). Команда: {effective_team}")
                if candidate_index_to_remove != -1:
                    remaining_candidates.pop(candidate_index_to_remove)
            else:
                print("Не найдено подходящих кандидатов для добавления на этой итерации.")
                break
        self.effective_team = effective_team
        print(f"Финальная эффективная команда ({len(effective_team)} героев): {effective_team}")
        print(f"Роли: Танки={tanks_count}, Саппорты={supports_count}, Атакеры={attackers_count}")
        print("--- Конец расчета эффективной команды ---")
        return effective_team


# Привязка методов отображения (если они где-то вызываются напрямую из логики)
CounterpickLogic.generate_counterpick_display = generate_counterpick_display
CounterpickLogic.generate_minimal_display = generate_minimal_display
CounterpickLogic.generate_minimal_icon_list = generate_minimal_icon_list