//! Реализация детектора особенностей на чистом Rust
//!
//! Этот модуль предоставляет настоящую реализацию AKAZE-подобного
//! алгоритма на чистом Rust без системных зависимостей.

use image::{DynamicImage, GrayImage};
use imageproc::contrast::equalize_histogram;
use log::{info, warn, debug, error};
use std::collections::HashMap;

/// Структура для хранения результатов AKAZE
#[derive(Debug, Clone)]
pub struct AkazeResult {
    pub keypoints: Vec<KeyPoint>,
    pub descriptors: Vec<Vec<u8>>,
}

/// Структура для ключевой точки (совместимая с текущим кодом)
#[derive(Debug, Clone)]
pub struct KeyPoint {
    pub x: u32,
    pub y: u32,
    pub strength: f32,
}

/// Структура для результатов сопоставления
#[derive(Debug, Clone)]
pub struct MatchResult {
    pub hero_name: String,
    pub match_count: usize,
    pub avg_distance: f32,
}

/// Параметры для AKAZE
#[derive(Debug, Clone)]
pub struct AkazeParams {
    pub min_match_count: usize,
    pub max_distance_ratio: f32,
}

impl Default for AkazeParams {
    fn default() -> Self {
        Self {
            min_match_count: 4,
            max_distance_ratio: 0.75,
        }
    }
}

/// Конвертирует DynamicImage в GrayImage для AKAZE
pub fn image_to_gray(image: &DynamicImage) -> GrayImage {
    image.to_luma8()
}

/// Вычисляет силу особенности в точке с использованием детерминанта гессиана
pub fn compute_hessian_strength(image: &GrayImage, x: u32, y: u32) -> f32 {
    let width = image.width();
    let height = image.height();

    if x < 1 || x >= width - 1 || y < 1 || y >= height - 1 {
        return 0.0;
    }

    // Вычисляем вторые производные
    let p = image.get_pixel(x, y)[0] as f32;
    let p_up = image.get_pixel(x, y - 1)[0] as f32;
    let p_down = image.get_pixel(x, y + 1)[0] as f32;
    let p_left = image.get_pixel(x - 1, y)[0] as f32;
    let p_right = image.get_pixel(x + 1, y)[0] as f32;
    let p_up_left = image.get_pixel(x - 1, y - 1)[0] as f32;
    let p_up_right = image.get_pixel(x + 1, y - 1)[0] as f32;
    let p_down_left = image.get_pixel(x - 1, y + 1)[0] as f32;
    let p_down_right = image.get_pixel(x + 1, y + 1)[0] as f32;

    // Вторые производные
    let dxx = p_right + p_left - 2.0 * p;
    let dyy = p_down + p_up - 2.0 * p;
    let dxy = (p_up_right + p_down_left - p_up_left - p_down_right) / 4.0;

    // Детерминант гессиана
    let det_hessian = dxx * dyy - dxy * dxy;

    det_hessian.abs()
}

/// Находит ключевые точки с помощью упрощенного детектора особенностей
pub fn find_keypoints(image: &GrayImage, threshold: f32) -> Vec<KeyPoint> {
    let mut keypoints = Vec::new();
    let width = image.width();
    let height = image.height();

    debug!("Поиск ключевых точек в изображении {}x{}", width, height);

    // Проходим по изображению с шагом 3 пикселя
    for y in (3..height - 3).step_by(3) {
        for x in (3..width - 3).step_by(3) {
            let strength = compute_hessian_strength(image, x, y);

            if strength > threshold {
                keypoints.push(KeyPoint { x, y, strength });
            }
        }
    }

    // Сортируем по силе и оставляем только сильнейшие точки
    keypoints.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap_or(std::cmp::Ordering::Equal));
    keypoints.truncate(1000); // Ограничиваем количество точек

    debug!("Найдено {} ключевых точек", keypoints.len());
    keypoints
}

/// Вычисляет бинарный дескриптор для ключевой точки
pub fn compute_binary_descriptor(image: &GrayImage, x: u32, y: u32, size: usize) -> Vec<u8> {
    let mut descriptor = Vec::new();
    let half_size = size / 2;

    for dy in -(half_size as i32)..=(half_size as i32) {
        for dx in -(half_size as i32)..=(half_size as i32) {
            let px = (x as i32 + dx).max(0).min(image.width() as i32 - 1) as u32;
            let py = (y as i32 + dy).max(0).min(image.height() as i32 - 1) as u32;

            let center_val = image.get_pixel(x, y)[0];
            let neighbor_val = image.get_pixel(px, py)[0];

            // Бинарный тест: 1 если сосед ярче центра, 0 иначе
            let bit = if neighbor_val > center_val { 1 } else { 0 };
            descriptor.push(bit);

            if descriptor.len() >= size {
                break;
            }
        }
        if descriptor.len() >= size {
            break;
        }
    }

    // Дополняем нулями если дескриптор слишком маленький
    while descriptor.len() < size {
        descriptor.push(0);
    }

    descriptor
}

/// Выполняет AKAZE детектирование и вычисление дескрипторов
pub fn detect_and_compute_akaze(
    image: &DynamicImage,
    params: &AkazeParams,
) -> Result<AkazeResult, Box<dyn std::error::Error>> {
    info!("=== AKAZE ДЕТЕКТИРОВАНИЕ И ВЫЧИСЛЕНИЕ ДЕСКРИПТОРОВ ===");

    // Конвертируем в grayscale и улучшаем контраст
    let gray_image = image_to_gray(image);
    let enhanced_image = equalize_histogram(&gray_image);

    // Находим ключевые точки
    let keypoints = find_keypoints(&enhanced_image, 50.0); // Фиксированный порог для простоты

    info!("Найдено {} ключевых точек AKAZE", keypoints.len());

    // Вычисляем дескрипторы для ключевых точек
    let mut descriptors = Vec::new();
    for kp in &keypoints {
        let descriptor = compute_binary_descriptor(&enhanced_image, kp.x, kp.y, 64);
        descriptors.push(descriptor);
    }

    info!("Вычислено {} дескрипторов", descriptors.len());

    Ok(AkazeResult {
        keypoints,
        descriptors,
    })
}

/// Вычисляет расстояние Хэмминга между двумя бинарными дескрипторами
pub fn hamming_distance(desc1: &[u8], desc2: &[u8]) -> u32 {
    let mut distance = 0u32;
    for (a, b) in desc1.iter().zip(desc2.iter()) {
        distance += (a ^ b) as u32;
    }
    distance
}

/// Сопоставляет дескрипторы двух изображений с помощью brute-force подхода
pub fn match_descriptors(
    descriptors1: &[Vec<u8>],
    descriptors2: &[Vec<u8>],
    max_distance_ratio: f32,
) -> Vec<(usize, usize, u32)> {
    let mut matches = Vec::new();

    for (i, desc1) in descriptors1.iter().enumerate() {
        let mut best_distance = u32::MAX;
        let mut second_best_distance = u32::MAX;
        let mut best_j = 0;

        // Находим два лучших совпадения для каждого дескриптора
        for (j, desc2) in descriptors2.iter().enumerate() {
            let distance = hamming_distance(desc1, desc2);

            if distance < best_distance {
                second_best_distance = best_distance;
                best_distance = distance;
                best_j = j;
            } else if distance < second_best_distance {
                second_best_distance = distance;
            }
        }

        // Применяем Lowe's ratio test
        if best_distance < second_best_distance &&
           (best_distance as f32) < max_distance_ratio * (second_best_distance as f32) {
            matches.push((i, best_j, best_distance));
        }
    }

    debug!("Найдено {} хороших совпадений", matches.len());
    matches
}

/// Сопоставляет шаблон героя с изображением скриншота
pub fn match_hero_template(
    template_image: &GrayImage,
    screen_result: &AkazeResult,
    hero_name: &str,
    params: &AkazeParams,
) -> Result<MatchResult, Box<dyn std::error::Error>> {
    info!("=== Сопоставление шаблона героя: {} ===", hero_name);

    // Улучшаем контраст шаблона
    let enhanced_template = equalize_histogram(template_image);

    // Находим ключевые точки в шаблоне
    let template_keypoints = find_keypoints(&enhanced_template, 50.0);

    if template_keypoints.is_empty() {
        warn!("В шаблоне героя {} не найдено ключевых точек", hero_name);
        return Ok(MatchResult {
            hero_name: hero_name.to_string(),
            match_count: 0,
            avg_distance: 0.0,
        });
    }

    // Вычисляем дескрипторы для шаблона
    let mut template_descriptors = Vec::new();
    for kp in &template_keypoints {
        let descriptor = compute_binary_descriptor(&enhanced_template, kp.x, kp.y, 64);
        template_descriptors.push(descriptor);
    }

    info!("В шаблоне найдено {} ключевых точек", template_keypoints.len());

    if template_descriptors.is_empty() || screen_result.descriptors.is_empty() {
        warn!("Пустые дескрипторы для героя {}", hero_name);
        return Ok(MatchResult {
            hero_name: hero_name.to_string(),
            match_count: 0,
            avg_distance: 0.0,
        });
    }

    // Сопоставляем дескрипторы
    let matches = match_descriptors(
        &template_descriptors,
        &screen_result.descriptors,
        params.max_distance_ratio,
    );

    // Вычисляем среднее расстояние
    let avg_distance = if !matches.is_empty() {
        let sum: u32 = matches.iter().map(|(_, _, dist)| *dist).sum();
        sum as f32 / matches.len() as f32
    } else {
        0.0
    };

    info!("Герой {}: {} совпадений, среднее расстояние: {:.2}",
          hero_name, matches.len(), avg_distance);

    Ok(MatchResult {
        hero_name: hero_name.to_string(),
        match_count: matches.len(),
        avg_distance,
    })
}

/// Основная функция для поиска героев на изображении
pub fn find_heroes_akaze(
    image: &DynamicImage,
    hero_templates: &HashMap<String, Vec<GrayImage>>,
    params: &AkazeParams,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    info!("=== НАЧАЛО ПОИСКА ГЕРОЕВ С AKAZE ===");

    // Выполняем AKAZE для основного изображения
    let screen_result = detect_and_compute_akaze(image, params)?;

    let mut detected_heroes = Vec::new();
    let mut hero_matches = Vec::new();

    // Проходим по всем шаблонам героев
    for (hero_name, templates) in hero_templates {
        info!("Обработка героя: {}", hero_name);

        let mut best_match_count = 0;
        let mut best_avg_distance = f32::MAX;

        // Пробуем каждый шаблон героя
        for (_i, template) in templates.iter().enumerate() {
            match match_hero_template(template, &screen_result, hero_name, params) {
                Ok(result) => {
                    if result.match_count > best_match_count {
                        best_match_count = result.match_count;
                        best_avg_distance = result.avg_distance;
                    }
                }
                Err(e) => {
                    error!("Ошибка при обработке шаблона героя {}: {}", hero_name, e);
                }
            }
        }

        // Проверяем порог совпадений
        if best_match_count >= params.min_match_count {
            detected_heroes.push(hero_name.clone());
            hero_matches.push((hero_name.clone(), best_match_count, best_avg_distance));
            info!("✓ Герой {} распознан: {} совпадений", hero_name, best_match_count);
        } else {
            info!("✗ Герой {} не распознан: {} совпадений", hero_name, best_match_count);
        }
    }

    // Сортируем по количеству совпадений
    hero_matches.sort_by(|a, b| b.1.cmp(&a.1));

    info!("=== РЕЗУЛЬТАТЫ AKAZE ===");
    for (hero, count, distance) in &hero_matches {
        info!("  {}: {} совпадений, расстояние: {:.2}", hero, count, distance);
    }

    Ok(detected_heroes)
}