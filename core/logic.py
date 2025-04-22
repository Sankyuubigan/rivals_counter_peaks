# File: core/logic.py
from collections import deque
# Импортируем данные напрямую
from heroes_bd import heroes, heroes_counters, hero_roles, heroes_compositions
# Импортируем переводы
from core.translations import get_text, DEFAULT_LANGUAGE as global_default_language
import cv2
import numpy as np
import os

# Константы остаются здесь
MIN_TANKS = 1
MAX_TANKS = 3
MIN_SUPPORTS = 2
MAX_SUPPORTS = 3
TEAM_SIZE = 6

class CounterpickLogic:
    def __init__(self):
        self.selected_heroes = deque(maxlen=TEAM_SIZE)
        self.priority_heroes = set()
        self.effective_team = []
        # Устанавливаем язык по умолчанию для этого экземпляра
        self.DEFAULT_LANGUAGE = global_default_language
        # Получаем версию приложения из переменной окружения
        self.APP_VERSION = os.environ.get("APP_VERSION", "N/A") # "N/A" если не найдена

    def set_selection(self, desired_selection):
        """
        Обновляет внутренний список выбранных героев (deque).
        """
        print(f"[Logic] set_selection called with: {desired_selection}")
        print(f"[Logic] Current internal selection (before): {list(self.selected_heroes)}")

        desired_set = set(desired_selection)
        desired_iterable = desired_selection if isinstance(desired_selection, (list, deque)) else list(desired_selection)

        new_deque = deque(maxlen=TEAM_SIZE)
        heroes_added_from_desired = set()

        # 1. Добавляем существующих
        for hero in list(self.selected_heroes):
            if hero in desired_set:
                new_deque.append(hero)
                heroes_added_from_desired.add(hero)

        # 2. Добавляем новых
        for hero in desired_iterable:
            if hero not in heroes_added_from_desired:
                if len(new_deque) < TEAM_SIZE:
                    new_deque.append(hero)
                else:
                    print(f"[Logic] WARN: Превышен лимит команды ({TEAM_SIZE}). Герой '{hero}' не добавлен.")
                    break

        self.selected_heroes = new_deque
        self.priority_heroes.intersection_update(set(self.selected_heroes))

        print(f"[Logic] Final internal selection: {list(self.selected_heroes)}")
        print(f"[Logic] Final priority: {self.priority_heroes}")
        self.effective_team = [] # Сбрасываем команду

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
            self.priority_heroes.discard(hero)
            print(f"[Logic] Priority removed from {hero}")
        else:
            self.priority_heroes.add(hero)
            print(f"[Logic] Priority set for {hero}")
        self.effective_team = []

    def get_selected_heroes_text(self):
        """Возвращает текст для метки 'Выбрано: ...'."""
        count = len(self.selected_heroes)
        heroes_list = list(self.selected_heroes)
        if not heroes_list:
            return get_text('selected', language=self.DEFAULT_LANGUAGE)
        else:
            header = f"{get_text('selected', language=self.DEFAULT_LANGUAGE)} ({count}/{TEAM_SIZE}): "
            return f"{header}{', '.join(heroes_list)}"

    def _calculate_hero_score(self, hero, current_selection_set, priority_heroes):
        """Рассчитывает очки для одного потенциального героя."""
        score = 0.0
        # Бонусы за контрпик врагов
        for enemy in current_selection_set:
            if hero in heroes_counters.get(enemy, []):
                score += 2.0 if enemy in priority_heroes else 1.0

        # Штраф, если герой сам выбран врагом
        if hero in current_selection_set:
            score -= 5.0

        # Штраф, если враги контрят этого героя
        counters_for_hero = heroes_counters.get(hero, [])
        for enemy in current_selection_set:
            if enemy in counters_for_hero:
                score -= 1.5 if enemy in priority_heroes else 1.0

        return score

    def calculate_counter_scores(self):
        """Рассчитывает рейтинг контрпиков для всех героев."""
        if not self.selected_heroes:
            return {}

        counter_scores = {}
        current_selection_set = set(self.selected_heroes)
        priority_heroes_set = self.priority_heroes # Сохраняем для передачи

        for hero in heroes: # Итерируем по всем героям из базы данных
            counter_scores[hero] = self._calculate_hero_score(hero, current_selection_set, priority_heroes_set)

        return counter_scores

    def calculate_effective_team(self, counter_scores):
        """Рассчитывает рекомендуемую команду."""
        if not counter_scores: # Если нет рассчитанных очков
            self.effective_team = []
            return []

        # Отбираем кандидатов: не враги с положительным рейтингом
        candidates = {
            hero: score for hero, score in counter_scores.items()
            if score > 0 and hero not in self.selected_heroes
        }

        if not candidates:
            self.effective_team = []
            return []

        # Сортируем кандидатов по убыванию рейтинга
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)

        effective_team = deque(maxlen=TEAM_SIZE)
        added_heroes_set = set()
        tanks_count, supports_count, attackers_count = 0, 0, 0

        # Шаг 1: Минимальные требования по ролям (сначала танк, потом саппорты)
        def role_priority_key(item):
            hero, score = item
            role_tanks = hero_roles.get("tanks", [])
            role_supports = hero_roles.get("supports", [])
            if hero in role_tanks: return (0, -score)
            if hero in role_supports: return (1, -score)
            return (2, -score)
        role_sorted_candidates = sorted(candidates.items(), key=role_priority_key)

        # Добавляем танка
        for hero, score in role_sorted_candidates:
             if tanks_count < MIN_TANKS and hero in hero_roles.get("tanks", []):
                 effective_team.append(hero); added_heroes_set.add(hero); tanks_count += 1
                 break

        # Добавляем саппортов
        support_added_count_step1 = 0
        for hero, score in role_sorted_candidates:
             if hero not in added_heroes_set and support_added_count_step1 < MIN_SUPPORTS and hero in hero_roles.get("supports", []):
                 effective_team.append(hero); added_heroes_set.add(hero); supports_count += 1; support_added_count_step1 += 1
                 if support_added_count_step1 >= MIN_SUPPORTS: break

        # Шаг 2: Добор до полной команды по рейтингу с учетом синергии и лимитов ролей
        remaining_candidates = [(h, s) for h, s in sorted_candidates if h not in added_heroes_set]

        while len(effective_team) < TEAM_SIZE and remaining_candidates:
            best_hero_to_add = None; best_adjusted_score = -float('inf'); candidate_index_to_remove = -1

            for i, (hero, score) in enumerate(remaining_candidates):
                 can_add = False; role = "unknown"
                 role_tanks = hero_roles.get("tanks", [])
                 role_supports = hero_roles.get("supports", [])
                 role_attackers = hero_roles.get("attackers", [])

                 if hero in role_tanks: role = "tanks"
                 elif hero in role_supports: role = "supports"
                 elif hero in role_attackers: role = "attackers"

                 # Проверяем лимиты ролей
                 if role == "tanks" and tanks_count < MAX_TANKS: can_add = True
                 elif role == "supports" and supports_count < MAX_SUPPORTS: can_add = True
                 elif role == "attackers": can_add = True # Нет верхнего лимита для атакеров
                 elif role == "unknown": can_add = True # Разрешаем добавлять героев без роли

                 if can_add:
                     # Рассчитываем бонус синергии
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
                # Обновляем счетчики добавленного героя
                if best_hero_to_add in hero_roles.get("tanks", []): tanks_count += 1
                elif best_hero_to_add in hero_roles.get("supports", []): supports_count += 1
                elif best_hero_to_add in hero_roles.get("attackers", []): attackers_count += 1
                # Удаляем добавленного из списка кандидатов
                if 0 <= candidate_index_to_remove < len(remaining_candidates):
                    remaining_candidates.pop(candidate_index_to_remove)
                else:
                    print(f"[WARN] Invalid index {candidate_index_to_remove} for remaining_candidates")
                    break # Ошибка индекса, выходим
            else:
                break # Не нашли подходящего кандидата

        self.effective_team = list(effective_team)
        return self.effective_team

    def recognize_heroes_from_image(self, image_cv2, hero_templates, threshold=0.8):
        """
        Ищет шаблоны героев на изображении image_cv2.
        """
        if image_cv2 is None:
            print("[ERROR][recognize] Входное изображение пустое.")
            return []
        if not hero_templates:
            print("[ERROR][recognize] Словарь шаблонов пуст.")
            return []

        recognized_heroes = set()
        try:
            image_gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
        except cv2.error as e:
            print(f"[ERROR][recognize] Ошибка конвертации изображения в серое: {e}")
            return []

        print(f"[RECOGNIZE] Начало распознавания. Изображение: {image_gray.shape}, Шаблонов: {len(hero_templates)}, Порог: {threshold}")

        for hero_name, templates in hero_templates.items():
            if hero_name in recognized_heroes and len(recognized_heroes) >= TEAM_SIZE : # Не ищем больше, если команда полная
                continue

            found_hero = False
            best_match_val = -1

            for i, template_cv2 in enumerate(templates):
                if template_cv2 is None: continue

                try:
                    template_gray = cv2.cvtColor(template_cv2, cv2.COLOR_BGR2GRAY)
                    if template_gray is None: continue
                    h, w = template_gray.shape

                    if h > image_gray.shape[0] or w > image_gray.shape[1]: continue

                    res = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                    if res is None: continue
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

                    if max_val > best_match_val: best_match_val = max_val

                    if max_val >= threshold:
                        print(f"[RECOGNIZE] НАЙДЕН: {hero_name} (шаблон {i}, уверенность: {max_val:.4f})")
                        recognized_heroes.add(hero_name)
                        found_hero = True
                        break # Нашли - переходим к следующему герою
                except cv2.error as e:
                     print(f"[ERROR][recognize] Ошибка OpenCV при обработке шаблона {i} для {hero_name}: {e}")
                except Exception as e:
                     print(f"[ERROR][recognize] Неожиданная ошибка при обработке шаблона {i} для {hero_name}: {e}")

        final_list = list(recognized_heroes)
        print(f"[RECOGNIZE] Распознавание завершено. Итог ({len(final_list)}): {final_list}")
        # Ограничиваем количество героев размером команды
        return final_list[:TEAM_SIZE]
