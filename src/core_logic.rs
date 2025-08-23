use crate::models::{AllHeroesData, HeroRoles, Role};
use std::collections::{HashMap, HashSet};

/// Рассчитывает "сырой" рейтинг для каждого героя против указанной команды врагов.
/// Логика основана на `test_manual_raiting.py`.
pub fn calculate_hero_ratings(
    enemy_team: &HashSet<String>,
    all_heroes_data: &AllHeroesData,
) -> HashMap<String, f32> {
    let mut hero_scores = HashMap::new();

    for (hero_name, _hero_data) in all_heroes_data {
        if enemy_team.contains(hero_name) {
            continue;
        }

        let mut total_score_contribution = 0.0;
        let mut matchups_found = 0;

        for enemy_hero_name in enemy_team {
            if let Some(enemy_hero_data) = all_heroes_data.get(enemy_hero_name) {
                if let Some(matchup) = enemy_hero_data
                    .opponents
                    .iter()
                    .find(|opp| opp.opponent == *hero_name)
                {
                    if let Ok(diff_val) = matchup.difference.replace('%', "").trim().parse::<f32>() {
                        // В скрипте `test_manual_raiting.py` значение инвертируется.
                        // Это означает, что положительная 'difference' в JSON - это плохо.
                        total_score_contribution -= diff_val;
                        matchups_found += 1;
                    }
                }
            }
        }

        if matchups_found > 0 {
            let avg_score = total_score_contribution / matchups_found as f32;
            hero_scores.insert(hero_name.clone(), avg_score);
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

        let context_factor = overall_winrate / 50.0;
        // `100.0 + score` так как score обычно отрицательный. Например, 100.0 + (-8.75) = 91.25
        let absolute_score = (100.0 + score) * context_factor;
        final_scores.push((hero.clone(), absolute_score));
    }

    // Сортируем по убыванию очков
    final_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    final_scores
}


const MIN_TANKS: usize = 1;
const MAX_SUPPORTS: usize = 3;
const MIN_SUPPORTS: usize = 2;
const TEAM_SIZE: usize = 6;

/// Выбирает оптимальную команду на основе рейтинга и ролей.
/// Реализует упрощенный, но надежный жадный алгоритм.
pub fn select_optimal_team(
    sorted_heroes: &[(String, f32)],
    hero_roles: &HeroRoles,
) -> Vec<String> {
    let mut team: Vec<(String, f32)> = Vec::new();
    let mut team_names = HashSet::new();

    // 1. Сначала добавляем обязательные роли из лучших кандидатов
    // Добавляем лучшего танка
    if let Some(best_tank) = sorted_heroes.iter().find(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Tank)) {
        if team_names.insert(best_tank.0.clone()) {
            team.push(best_tank.clone());
        }
    }
    // Добавляем лучших саппортов
    let best_supports: Vec<_> = sorted_heroes.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Support)).take(MIN_SUPPORTS).cloned().collect();
    for support in best_supports {
        if team_names.insert(support.0.clone()) {
            team.push(support);
        }
    }

    // 2. Создаем пул оставшихся кандидатов
    let mut remaining_pool: Vec<_> = sorted_heroes
        .iter()
        .filter(|(name, _)| !team_names.contains(name))
        .cloned()
        .collect();
    
    // 3. Жадным алгоритмом заполняем оставшиеся слоты
    while team.len() < TEAM_SIZE && !remaining_pool.is_empty() {
        let best_candidate = remaining_pool.remove(0); // Уже отсортировано по очкам
        let role = hero_roles.roles.get(&best_candidate.0).unwrap_or(&Role::Unknown);
        
        let support_count = team.iter().filter(|(h, _)| hero_roles.roles.get(h) == Some(&Role::Support)).count();

        // Проверяем ограничения
        let can_add = match role {
            Role::Support if support_count < MAX_SUPPORTS => true,
            Role::Tank | Role::Dd => true,
            _ => false,
        };

        if can_add {
             if team_names.insert(best_candidate.0.clone()) {
                team.push(best_candidate);
            }
        }
    }
    
    // 4. Если команда все еще не полная, просто добавляем лучших из оставшихся
    if team.len() < TEAM_SIZE {
        for hero in remaining_pool.iter() {
            if team.len() >= TEAM_SIZE { break; }
            if team_names.insert(hero.0.clone()) {
                team.push(hero.clone());
            }
        }
    }

    team.into_iter().map(|(name, _)| name).collect()
}