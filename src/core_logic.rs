use crate::models::{AllHeroesData, HeroRoles, Role};
use std::collections::{HashMap, HashSet};

/// Рассчитывает рейтинг для каждого героя против указанной команды врагов.
/// Логика основана на анализе контр-пиков: положительный рейтинг означает преимущество.
pub fn calculate_hero_ratings(
    enemy_team: &[String],
    all_heroes_data: &AllHeroesData,
) -> HashMap<String, f32> {
    let mut hero_scores = HashMap::new();

    // Итерируем по всем героям в базе данных, это наши кандидаты
    for (candidate_hero_name, candidate_hero_data) in all_heroes_data {
        // Не оцениваем героев, которые уже находятся в команде врага
        if enemy_team.contains(candidate_hero_name) {
            continue;
        }

        let mut total_score_contribution = 0.0;
        let mut matchups_found = 0;

        // Для каждого кандидата проверяем его эффективность против каждого врага
        for enemy_hero_name in enemy_team {
            // Ищем данные о матчапе "кандидат против врага"
            if let Some(matchup) = candidate_hero_data
                .opponents
                .iter()
                .find(|opp| &opp.opponent == enemy_hero_name)
            {
                if let Ok(diff_val) = matchup.difference.replace('%', "").trim().parse::<f32>() {
                    // ИСПРАВЛЕНИЕ 1: Инвертируем значение, как в эталонном скрипте.
                    // Положительное значение 'difference' в JSON означает, что ВРАГ имеет преимущество.
                    // Мы инвертируем его, чтобы положительный score означал преимущество для НАШЕГО кандидата.
                    total_score_contribution += -diff_val;
                    matchups_found += 1;
                }
            }
        }

        // Если найдены матчапы, вычисляем средний балл и сохраняем
        if matchups_found > 0 {
            let avg_score = total_score_contribution / matchups_found as f32;
            hero_scores.insert(candidate_hero_name.clone(), avg_score);
        }
    }

    hero_scores
}


/// Применяет контекст (общий винрейт героя) к "сырым" очкам.
/// Логика основана на `absolute_with_context` из `test_manual_raiting.py`.
pub fn apply_context_to_scores(
    scores: &HashMap<String, f32>,
    all_heroes_data: &AllHeroesData,
) -> Vec<(String, f32)> {
    let mut final_scores = Vec::new();

    for (hero, score) in scores {
        let overall_winrate = all_heroes_data
            .get(hero)
            .and_then(|data| data.win_rate.replace('%', "").trim().parse::<f32>().ok())
            .unwrap_or(50.0);

        // Чем сильнее герой в целом, тем ценнее его положительный вклад
        let context_factor = overall_winrate / 50.0;
        
        // ИСПРАВЛЕНИЕ 2: Используем базовое значение 100.0, как в эталонном скрипте.
        // `score` - это преимущество/недостаток.
        let absolute_score = (100.0 + score) * context_factor;
        final_scores.push((hero.clone(), absolute_score));
    }

    // Сортируем по убыванию очков
    final_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    final_scores
}

const TEAM_SIZE: usize = 6;
const MIN_SUPPORTS: usize = 2;
const MAX_SUPPORTS: usize = 3;

/// Выбирает оптимальную команду на основе рейтинга и ролей, как в test_manual_raiting.py.
/// Алгоритм перебирает наилучшие комбинации ролей.
pub fn select_optimal_team(
    sorted_heroes: &[(String, f32)],
    hero_roles: &HeroRoles,
) -> Vec<String> {
    let tanks: Vec<_> = sorted_heroes.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Tank)).cloned().collect();
    let supports: Vec<_> = sorted_heroes.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Support)).cloned().collect();
    let dds: Vec<_> = sorted_heroes.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Dd) || hero_roles.roles.get(h) == Some(&Role::Unknown)).cloned().collect();

    let mut best_team_composition: Vec<(String, f32)> = Vec::new();
    let mut best_score = f32::NEG_INFINITY;

    // Возможные комбинации (танки, саппорты, дд), удовлетворяющие условиям:
    // V >= 1, 2 <= S <= 3, V + S + D = 6
    // Эта логика полностью соответствует комбинациям, генерируемым в Python скрипте
    let possible_combinations = [
        (1, 2, 3), (1, 3, 2), (2, 2, 2), (2, 3, 1),
        (3, 2, 1), (3, 3, 0), (4, 2, 0),
    ];

    for &(v_count, s_count, d_count) in &possible_combinations {
        if tanks.len() >= v_count && supports.len() >= s_count && dds.len() >= d_count {
            let mut current_team = Vec::new();
            current_team.extend(tanks.iter().take(v_count));
            current_team.extend(supports.iter().take(s_count));
            current_team.extend(dds.iter().take(d_count));

            let current_score: f32 = current_team.iter().map(|(_, score)| *score).sum();

            if current_score > best_score {
                best_score = current_score;
                best_team_composition = current_team.into_iter().cloned().collect();
            }
        }
    }
    
    // Если подходящая команда найдена, возвращаем ее
    if !best_team_composition.is_empty() {
        return best_team_composition.into_iter().map(|(name, _)| name).collect();
    }

    // Резервная логика (жадный алгоритм), если ни одна комбинация не сработала
    let mut team: Vec<(String, f32)> = Vec::new();
    let mut team_names = HashSet::new();

    // 1. Обязательный танк
    if let Some(best_tank) = tanks.first() {
        if team_names.insert(best_tank.0.clone()) {
            team.push(best_tank.clone());
        }
    }
    // 2. Обязательные саппорты
    for support in supports.iter().take(MIN_SUPPORTS) {
        if team_names.insert(support.0.clone()) {
            team.push(support.clone());
        }
    }
    
    // 3. Добираем остальных из общего пула лучших героев
    let mut remaining_pool: Vec<_> = sorted_heroes
        .iter()
        .filter(|(name, _)| !team_names.contains(name))
        .cloned()
        .collect();

    while team.len() < TEAM_SIZE && !remaining_pool.is_empty() {
        let best_candidate = remaining_pool.remove(0);
        let role = hero_roles.roles.get(&best_candidate.0);
        
        let support_count = team.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Support)).count();

        // Проверяем ограничение на максимальное количество саппортов
        if role == Some(&Role::Support) && support_count >= MAX_SUPPORTS {
            continue;
        }
        
        if team_names.insert(best_candidate.0.clone()) {
            team.push(best_candidate);
        }
    }

    team.into_iter().map(|(name, _)| name).collect()
}