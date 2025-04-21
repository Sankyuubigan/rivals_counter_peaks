# File: logic.py
from collections import deque # Используем deque для selected_heroes
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
from translations import get_text, DEFAULT_LANGUAGE as global_default_language
# <<< ДОБАВЛЕНО: Импорты для распознавания >>>
import cv2
import numpy as np
# <<< ------------------------------------ >>>
import os # Для получения версии

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
        # Сохраняем текущий язык для сообщений
        self.DEFAULT_LANGUAGE = global_default_language
        # Получаем версию из окружения (устанавливается в build.py)
        self.APP_VERSION = os.environ.get("APP_VERSION", "N/A")

    def set_selection(self, desired_selection):
        """
        Обновляет внутренний список выбранных героев (deque),
        чтобы он соответствовал переданному множеству или списку из UI/распознавания.
        Сохраняет порядок добавления новых и учитывает TEAM_SIZE.
        """
        print(f"[Logic] set_selection called with: {desired_selection}")
        print(f"[Logic] Current internal selection (before): {list(self.selected_heroes)}")

        # Преобразуем входные данные в set для быстрой проверки наличия
        desired_set = set(desired_selection)
        # Если порядок важен (например, для deque), используем исходный список/deque
        desired_iterable = desired_selection if isinstance(desired_selection, (list, deque)) else list(desired_selection)

        # Создаем новый deque на основе текущего состояния UI, сохраняя порядок старых
        new_deque = deque(maxlen=TEAM_SIZE)
        heroes_added_from_desired = set()

        # 1. Добавляем существующих героев из старого deque, если они есть в новом наборе
        for hero in list(self.selected_heroes):  # Итерируемся по копии старого deque
            if hero in desired_set:
                new_deque.append(hero)
                heroes_added_from_desired.add(hero)

        # 2. Добавляем новых героев (которые есть в desired, но не были в старом deque) в конец
        for hero in desired_iterable:
            if hero not in heroes_added_from_desired:
                # Проверяем, есть ли место в deque перед добавлением
                if len(new_deque) < TEAM_SIZE:
                    new_deque.append(hero)  # deque сам обработает maxlen, но лучше проверить явно
                else:
                    print(f"[Logic] WARN: Превышен лимит команды ({TEAM_SIZE}). Герой '{hero}' не добавлен.")
                    break  # Прерываем добавление, если достигли лимита


        # 3. Обновляем основной deque
        self.selected_heroes = new_deque

        # 4. Обновляем приоритеты: оставляем только тех, кто все еще выбран
        self.priority_heroes.intersection_update(set(self.selected_heroes))

        print(f"[Logic] Final internal selection: {list(self.selected_heroes)}")
        print(f"[Logic] Final priority: {self.priority_heroes}")

        # Сбрасываем эффективную команду, т.к. выбор изменился
        self.effective_team = []   

    def clear_all(self):
        """Очищает все выборы и приоритеты."""
        print("[Logic] Clearing all selections.")
        self.selected_heroes.clear()
        self.priority_heroes.clear()
        self.effective_team = []

    def set_priority(self, hero):
        """Устанавливает или снимает приоритет героя."""
        if hero not in self.selected_heroes:
            print(f"[Logic] Cannot set priority for non-selected hero: {hero}")
            return

        if hero in self.priority_heroes:
            self.priority_heroes.discard(hero) # Используем discard для set
            print(f"[Logic] Priority removed from {hero}")
        else:
            self.priority_heroes.add(hero) # Используем add для set
            print(f"[Logic] Priority set for {hero}")
        # Сбрасываем эффективную команду, т.к. приоритеты влияют на расчет
        self.effective_team = []


    def get_selected_heroes_text(self):
        """Возвращает текст для метки 'Выбрано: ...'."""        
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes)  # Преобразуем deque в список для join
        if not heroes_list:
            return get_text('selected', language=self.DEFAULT_LANGUAGE)  # "Выбрано"
        else:
            header = f"{get_text('selected', language=self.DEFAULT_LANGUAGE)} ({count}/{TEAM_SIZE}): "
            return f"{header}{', '.join(heroes_list)}"
    
    def _calculate_counter_score(self, selected_enemy):
        """Рассчитывает очки за контрпики для одного выбранного врага."""
        counter_scores = {}
        for counter_pick in heroes_counters.get(selected_enemy, []):
            # Увеличиваем очки: +2 за приоритетного врага, +1 за обычного
            score_increase = 2.0 if selected_enemy in self.priority_heroes else 1.0            
            counter_scores.setdefault(counter_pick, 0.0)
            counter_scores[counter_pick] += score_increase
        return counter_scores
    
    def _sort_counters(self, hero, current_selection_set, counter_scores):
        """Применяет штрафы к рейтингу контрпиков."""
        if hero not in counter_scores: return # Штрафуем только тех, кто есть в списке героев

        # Штраф, если потенциальный пик сам является выбранным врагом
        if hero in current_selection_set:
            counter_scores[hero] -= 5.0  # Большой штраф

        # Штраф за каждого врага, который контрит потенциальный пик
        counters_for_potential_pick = heroes_counters.get(hero, [])
        for selected_enemy in self.selected_heroes:
            if selected_enemy in counters_for_potential_pick:
                # Уменьшаем очки: -1.5 за контру от приоритетного врага, -1 за контру от обычного
                score_decrease = 1.5 if selected_enemy in self.priority_heroes else 1.0
                counter_scores[hero] -= score_decrease
        
    def _find_best_counter_by_hero(self, counter_scores, current_selection_set):
        for potential_pick in heroes:
             self._sort_counters(potential_pick, current_selection_set, counter_scores)            


    def calculate_counter_scores(self):
        """Рассчитывает рейтинг контрпиков."""
        if not self.selected_heroes:
            return {} # Возвращаем пустой словарь, если нет выбранных

        counter_scores = {hero: 0.0 for hero in heroes}
        current_selection_set = set(self.selected_heroes)  # Для быстрой проверки

        # Шаг 1: Начисляем очки за контру выбранных врагов
        for selected_enemy in self.selected_heroes:
            new_counter_scores = self._calculate_counter_score(selected_enemy)
            counter_scores.update(new_counter_scores)

        self._find_best_counter_by_hero(counter_scores, current_selection_set)
        
        return counter_scores


    def calculate_effective_team(self, counter_scores):        
        """Рассчитывает рекомендуемую команду с учетом ролей и синергии."""
        # print("--- Logic: Calculating effective team ---")
        # Отбираем кандидатов: не враги с положительным рейтингом
        candidates = {
            hero: score for hero, score in counter_scores.items()
            if score > 0 and hero not in self.selected_heroes
        }

        if not candidates:
            self.effective_team = []
            # print("Logic: No positive candidates found after filtering selected heroes.")
            return []

        # Сортируем кандидатов по убыванию рейтинга (основной критерий)
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)

        effective_team = deque(maxlen=TEAM_SIZE)
        added_heroes_set = set()
        tanks_count, supports_count, attackers_count = 0, 0, 0

        # Шаг 1: Минимальные требования по ролям (танк и саппорты)
        # Сортируем кандидатов с приоритетом ролей (Танк > Саппорт > Атакер)
        def role_priority_key(item):
            hero, score = item
            if hero in hero_roles.get("tanks", []): return (0, -score) # 0 - танк, сортируем по убыванию score
            if hero in hero_roles.get("supports", []): return (1, -score) # 1 - саппорт
            return (2, -score) # 2 - остальные (атакеры)
        role_sorted_candidates = sorted(candidates.items(), key=role_priority_key)

        # Добавляем минимум 1 танка
        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []):
                 effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1                
                 break # Добавили одного - выходим

        # Добавляем минимум 2 саппортов
        support_added_count_step1 = 0
        for hero, score in role_sorted_candidates:
             # Проверяем, что герой еще не добавлен
             if hero not in added_heroes_set and support_added_count_step1 < MIN_SUPPORTS and hero in hero_roles.get("supports", []):
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1; support_added_count_step1 += 1                
                 if support_added_count_step1 >= MIN_SUPPORTS: break # Добавили нужное количество - выходим

        # Шаг 2: Добор до полной команды по рейтингу с учетом ролей и синергии
        # Используем изначально отсортированных по рейтингу кандидатов (sorted_candidates)
        remaining_candidates = [(h, s) for h, s in sorted_candidates if h not in added_heroes_set]

        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1

            # Ищем лучшего кандидата из оставшихся
            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = "unknown"
                 if hero in hero_roles.get("tanks", []): role = "tanks"
                 elif hero in hero_roles.get("supports", []): role = "supports"
                 elif hero in hero_roles.get("attackers", []): role = "attackers"

                 # Проверяем ограничения по ролям
                 if role == "tanks" and tanks_count < MAX_TANKS: can_add = True
                 elif role == "supports" and supports_count < MAX_SUPPORTS: can_add = True
                 # Для атакующих нет верхнего предела (кроме общего размера команды)
                 elif role == "attackers": can_add = True
                 elif role == "unknown": can_add = True # Добавляем, если роль неизвестна

                 if can_add:
                     # Считаем бонус синергии с УЖЕ ДОБАВЛЕННЫМИ в команду
                     synergy_bonus = 0
                     for teammate in effective_team:
                         # Проверяем в обе стороны
                         if hero in heroes_compositions.get(teammate, []): synergy_bonus += 0.5
                         if teammate in heroes_compositions.get(hero, []): synergy_bonus += 0.5

                     adjusted_score = score + synergy_bonus
                     if adjusted_score > best_adjusted_score:
                         best_adjusted_score = adjusted_score; best_hero_to_add = hero; candidate_index_to_remove = i

            # Добавляем лучшего найденного кандидата, если он есть
            if best_hero_to_add is not None:
                effective_team.append(best_hero_to_add)
                added_heroes_set.add(best_hero_to_add)
                # Обновляем счетчики ролей
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1                
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1
                # Удаляем добавленного героя из списка кандидатов
                if candidate_index_to_remove != -1:
                    remaining_candidates.pop(candidate_index_to_remove)
            else:
                # Если не нашли подходящего кандидата (например, из-за лимитов ролей), прерываем цикл
                break

        self.effective_team = list(effective_team)
        # print(f"Logic: Final effective team ({len(self.effective_team)}): {self.effective_team}")
        # print(f"Logic: Roles: T={tanks_count}, S={supports_count}, A={attackers_count}")
        # print("--- Logic: End calculating effective team ---")
        return self.effective_team

    # <<< ДОБАВЛЕНО: Функция распознавания героев >>>
    def recognize_heroes_from_image(self, image_cv2, hero_templates, threshold=0.8):
        """
        Ищет шаблоны героев на изображении image_cv2.

        Args:
            image_cv2 (np.array): Изображение (скриншот) в формате OpenCV (BGR).
            hero_templates (dict): Словарь {hero_name: [template1_cv2, template2_cv2, ...]}.
            threshold (float): Порог уверенности для cv2.matchTemplate (0.0-1.0).

        Returns:
            list: Список уникальных имен распознанных героев.
        """
        if image_cv2 is None:
            print("[ERROR][recognize] Входное изображение пустое.")
            return []
        if not hero_templates:
            print("[ERROR][recognize] Словарь шаблонов пуст.")
            return []

        recognized_heroes = set()
        # Преобразуем изображение в оттенки серого для matchTemplate
        image_gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
        
        print(f"[RECOGNIZE] Начало распознавания. Изображение: {image_gray.shape}, Шаблонов: {len(hero_templates)}, Порог: {threshold}")

        # Проходим по каждому герою и его шаблонам
        for hero_name, templates in hero_templates.items():
            if hero_name in recognized_heroes: # Пропускаем, если уже нашли этого героя
                continue

            found_hero = False
            best_match_val = -1 # Для отладки лучшего совпадения для героя

            for i, template_cv2 in enumerate(templates):
                if template_cv2 is None:
                    # print(f"[WARN][recognize] Пропущен пустой шаблон {i} для героя {hero_name}")
                    continue

                try:
                    # Шаблон тоже преобразуем в серый
                    template_gray = cv2.cvtColor(template_cv2, cv2.COLOR_BGR2GRAY)
                    h, w = template_gray.shape

                    # Проверка: шаблон не должен быть больше изображения
                    if h > image_gray.shape[0] or w > image_gray.shape[1]:
                         # print(f"[WARN][recognize] Шаблон {i} для {hero_name} ({w}x{h}) больше изображения ({image_gray.shape[1]}x{image_gray.shape[0]}). Пропуск.")
                         continue                        

                    # Сопоставление шаблона методом TM_CCOEFF_NORMED
                    # Результат - карта совпадений, где самое яркое место - лучшее совпадение
                    res = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                    # Находим максимальное значение совпадения на карте
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

                    # Обновляем лучшее значение для этого героя (для отладки)
                    if max_val > best_match_val:
                        best_match_val = max_val

                    # print(f"[DEBUG][recognize] Герой: {hero_name}, Шаблон: {i}, MaxVal: {max_val:.4f}") # Детальный лог

                    # Если уверенность выше порога, считаем героя найденным
                    if max_val >= threshold:
                        print(f"[RECOGNIZE] НАЙДЕН: {hero_name} (шаблон {i}, уверенность: {max_val:.4f})")
                        recognized_heroes.add(hero_name)
                        found_hero = True
                        break # Нашли героя по одному из шаблонов, переходим к следующему герою
                except cv2.error as e:
                     print(f"[ERROR][recognize] Ошибка OpenCV при обработке шаблона {i} для {hero_name}: {e}")
                except Exception as e:
                     print(f"[ERROR][recognize] Неожиданная ошибка при обработке шаблона {i} для {hero_name}: {e}")

            # Если герой не найден ни по одному шаблону (для отладки)
            # if not found_hero:
            #     print(f"[RECOGNIZE] Не найден: {hero_name} (лучшее совпадение: {best_match_val:.4f})")


        print(f"[RECOGNIZE] Распознавание завершено. Итог: {list(recognized_heroes)}")
        # Возвращаем список уникальных имен (порядок может быть не важен)
        final_list = list(recognized_heroes)
        # Ограничиваем количество распознанных героев размером команды
        return final_list[:TEAM_SIZE]
    # <<< КОНЕЦ Функции распознавания >>>
