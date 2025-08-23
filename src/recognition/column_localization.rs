use anyhow::Result;
use image::{DynamicImage, GrayImage};
use imageproc::contrast::equalize_histogram;
use std::collections::HashMap;
use std::path::Path;
use crate::utils::get_absolute_path_string;
use log::{info, warn, debug, error};
use crate::recognition::akaze_analysis::{get_recommended_params, AkazeParams};

/// Глобальные параметры AKAZE (используем lazy_static для безопасной инициализации)
use std::sync::OnceLock;
static PARAMS: OnceLock<AkazeParams> = OnceLock::new();

/// Получает параметры AKAZE
fn get_akaze_params() -> &'static AkazeParams {
    PARAMS.get_or_init(|| get_recommended_params())
}

/// Структура для хранения результатов локализации колонки
pub struct ColumnLocalizationResult {
    pub column_x_center: Option<u32>,
    pub detected_heroes: Vec<String>,
}
/// Структура для хранения ключевой точки
#[derive(Debug, Clone)]
struct KeyPoint {
    x: u32,
    y: u32,
    strength: f32,
}
/// Структура для хранения дескриптора
#[derive(Debug, Clone)]
struct Descriptor {
    data: Vec<u8>,
}
/// Локализует колонку с героями с помощью упрощенного детектора особенностей
pub fn localize_hero_column(image: &DynamicImage) -> Result<ColumnLocalizationResult> {
    info!("=== НАЧАЛО ЛОКАЛИЗАЦИИ КОЛОНКИ (AKAZE) ===");
    
    // Получаем параметры динамически
    let params = get_akaze_params();
    info!("Используемые параметры:");
    info!("  Порог силы особенности: {:.1}", params.feature_threshold);
    info!("  Порог сопоставления: {:.1}", params.match_threshold);
    info!("  Мин. совпадений: {}", params.min_match_count);
    info!("  Размер дескриптора: {}", params.descriptor_size);
    info!("  Мин. героев для колонки: {}", params.min_heroes_for_column);
    
    // Загружаем шаблоны героев
    info!("Начало загрузки шаблонов героев...");
    let hero_templates = load_hero_templates()?;
    
    if hero_templates.is_empty() {
        error!("Словарь шаблонов пуст. Локализация колонки невозможна.");
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes: Vec::new(),
        });
    }
    
    info!("Загружено шаблонов для {} героев", hero_templates.len());
    for (hero_name, templates) in &hero_templates {
        info!("  - {}: {} шаблон(ов)", hero_name, templates.len());
        for (i, template) in templates.iter().enumerate() {
            info!("    Шаблон #{}: {}x{}", i + 1, template.width(), template.height());
        }
    }
    
    // Конвертируем изображение в оттенки серого
    let gray_image = image.to_luma8();
    info!("Изображение преобразовано в оттенки серого: {}x{}", gray_image.width(), gray_image.height());
    
    // Улучшаем контраст
    let enhanced_image = equalize_histogram(&gray_image);
    info!("Применена эквализация гистограммы");
    
    // Находим ключевые точки на скриншоте
    info!("Поиск ключевых точек на скриншоте...");
    let screen_keypoints = find_keypoints_with_params(&enhanced_image, params.feature_threshold);
    info!("Найдено {} ключевых точек на скриншоте", screen_keypoints.len());
    
    // Выводим информацию о сильнейших ключевых точках для отладки
    if !screen_keypoints.is_empty() {
        info!("Топ-10 сильнейших ключевых точек на скриншоте:");
        for (i, kp) in screen_keypoints.iter().take(10).enumerate() {
            info!("  {}. ({}, {}) сила: {:.2}", i + 1, kp.x, kp.y, kp.strength);
        }
    } else {
        warn!("Ключевые точки на скриншоте не найдены!");
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes: Vec::new(),
        });
    }
    
    // Вычисляем дескрипторы для скриншота
    info!("Вычисление дескрипторов для скриншота...");
    let screen_descriptors: Vec<Descriptor> = screen_keypoints
        .iter()
        .map(|kp| compute_descriptor_with_params(&enhanced_image, kp.x, kp.y, params.descriptor_size))
        .collect();
    
    info!("Вычислено {} дескрипторов для скриншота", screen_descriptors.len());
    
    if screen_descriptors.is_empty() {
        error!("Не удалось вычислить дескрипторы для скриншота");
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes: Vec::new(),
        });
    }
    
    let mut all_x_coords = Vec::new();
    let mut detected_heroes = Vec::new();
    let mut hero_matches = Vec::new();
    
    // Ищем совпадения для каждого героя
    info!("=== ПОИСК СОВПАДЕНИЙ ДЛЯ КАЖДОГО ГЕРОЯ ===");
    for (hero_name, template_images) in &hero_templates {
        info!("=== Поиск совпадений для героя: {} ===", hero_name);
        info!("Доступно шаблонов: {}", template_images.len());
        
        let mut best_match_count = 0;
        let mut best_x_coords = Vec::new();
        let mut template_matches_info = Vec::new();
        
        for (template_idx, template_image) in template_images.iter().enumerate() {
            info!("  Обработка шаблона #{}", template_idx + 1);
            info!("    Размер шаблона: {}x{}", template_image.width(), template_image.height());
            
            // Находим ключевые точки для шаблона
            let template_keypoints = find_keypoints_with_params(template_image, params.feature_threshold);
            
            if template_keypoints.is_empty() {
                warn!("    В шаблоне не найдено ключевых точек");
                continue;
            }
            
            info!("    Найдено {} ключевых точек в шаблоне", template_keypoints.len());
            
            // Вычисляем дескрипторы для шаблона
            let template_descriptors: Vec<Descriptor> = template_keypoints
                .iter()
                .map(|kp| compute_descriptor_with_params(template_image, kp.x, kp.y, params.descriptor_size))
                .collect();
            
            info!("    Вычислено {} дескрипторов для шаблона", template_descriptors.len());
            
            if template_descriptors.is_empty() {
                warn!("    Не удалось вычислить дескрипторы для шаблона");
                continue;
            }
            
            // Ищем совпадения
            let matches = find_matches_with_params(&template_descriptors, &screen_descriptors, params.match_threshold);
            
            info!("    Найдено {} совпадений", matches.len());
            
            if matches.len() > best_match_count {
                best_match_count = matches.len();
                best_x_coords = matches.iter()
                    .map(|m| screen_keypoints[m.screen_idx].x as f32)
                    .collect();
            }
            
            template_matches_info.push((template_idx + 1, matches.len()));
        }
        
        info!("  Результаты для {}: лучшее количество совпадений = {}", hero_name, best_match_count);
        for (template_idx, count) in template_matches_info {
            info!("    Шаблон {}: {} совпадений", template_idx, count);
        }
        
        if best_match_count >= params.min_match_count {
            hero_matches.push((hero_name.clone(), best_match_count));
            detected_heroes.push(hero_name.clone());
            all_x_coords.extend(best_x_coords);
            info!("✓ Герой '{}' распознан с {} совпадениями", hero_name, best_match_count);
        } else {
            info!("✗ Герой '{}' не распознан (недостаточно совпадений: {} < {})", 
                   hero_name, best_match_count, params.min_match_count);
        }
    }
    
    // Сортируем по количеству совпадений
    hero_matches.sort_by(|a, b| b.1.cmp(&a.1));
    
    // Логируем результаты
    info!("=== РЕЗУЛЬТАТЫ AKAZE ===");
    for (i, (hero, count)) in hero_matches.iter().enumerate() {
        info!("  {}. {} - {} совпадений", i + 1, hero, count);
    }
    
    if detected_heroes.is_empty() {
        warn!("НИ ОДНОГО ГЕРОЯ НЕ БЫЛО РАСПОЗНАНО AKAZE!");
        info!("Возможные причины:");
        info!("1. Слишком высокий порог силы особенности");
        info!("2. Слишком строгий порог сопоставления дескрипторов");
        info!("3. Неправильные размеры или качество шаблонов");
        info!("4. Проблемы с освещением или масштабом на скриншоте");
    }
    
    if detected_heroes.len() < params.min_heroes_for_column {
        warn!("Недостаточно героев для надежной локализации колонки: {} < {}", 
              detected_heroes.len(), params.min_heroes_for_column);
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
        });
    }
    
    // Находим наиболее частую X-координату
    let column_center = find_most_common_x(&all_x_coords);
    
    if let Some(center) = column_center {
        info!("Центр колонки определен на X-координате: {}", center);
        Ok(ColumnLocalizationResult {
            column_x_center: Some(center),
            detected_heroes,
        })
    } else {
        warn!("Не удалось определить центр колонки");
        Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
        })
    }
}
/// Загружает шаблоны героев
fn load_hero_templates() -> Result<HashMap<String, Vec<GrayImage>>> {
    let mut templates = HashMap::new();
    let templates_dir = get_absolute_path_string("resources/heroes_icons");
    
    info!("Попытка загрузки шаблонов из директории: {}", templates_dir);
    
    if !Path::new(&templates_dir).exists() {
        error!("Директория с шаблонами не найдена: {}", templates_dir);
        return Ok(templates);
    }
    
    let entries = std::fs::read_dir(&templates_dir);
    if let Err(e) = entries {
        error!("Не удалось прочитать директорию с шаблонами: {}", e);
        return Ok(templates);
    }
    
    let mut file_count = 0;
    let mut loaded_count = 0;
    
    for entry in entries.unwrap() {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                error!("Ошибка при чтении записи в директории: {}", e);
                continue;
            }
        };
        
        let path = entry.path();
        file_count += 1;
        
        if path.is_file() {
            if let Some(file_name) = path.file_name().and_then(|n| n.to_str()) {
                info!("Обработка файла: {}", file_name);
                
                let parts: Vec<&str> = file_name.split('_').collect();
                if parts.len() >= 2 {
                    let hero_name = parts[0..parts.len()-1].join("_");
                    let extension = path.extension().and_then(|s| s.to_str()).unwrap_or("");
                    
                    info!("  Определенное имя героя: '{}'", hero_name);
                    info!("  Расширение файла: '{}'", extension);
                    
                    if extension == "png" || extension == "jpg" || extension == "jpeg" {
                        match image::open(&path) {
                            Ok(img) => {
                                let gray_img = img.to_luma8();
                                templates.entry(hero_name).or_insert_with(Vec::new).push(gray_img);
                                loaded_count += 1;
                                info!("  ✓ Шаблон успешно загружен: {}x{}", img.width(), img.height());
                            }
                            Err(e) => {
                                error!("  ✗ Не удалось загрузить изображение '{}': {}", file_name, e);
                            }
                        }
                    } else {
                        warn!("  ✗ Неподдерживаемое расширение файла: '{}'", extension);
                    }
                } else {
                    warn!("  ✗ Некорректный формат имени файла: '{}'", file_name);
                }
            }
        }
    }
    
    info!("Статистика загрузки шаблонов:");
    info!("  Всего файлов найдено: {}", file_count);
    info!("  Успешно загружено: {}", loaded_count);
    info!("  Уникальных героев: {}", templates.len());
    
    Ok(templates)
}
/// Находит ключевые точки с использованием динамических параметров
fn find_keypoints_with_params(image: &GrayImage, feature_threshold: f32) -> Vec<KeyPoint> {
    let mut keypoints = Vec::new();
    
    let width = image.width();
    let height = image.height();
    
    debug!("Поиск ключевых точек в изображении {}x{} с порогом {}", width, height, feature_threshold);
    
    // Проходим по изображению с шагом 5 пикселей
    for y in (5..height-5).step_by(5) {
        for x in (5..width-5).step_by(5) {
            // Вычисляем силу особенности как вариацию яркости в окрестности
            let mut sum = 0.0;
            let mut count = 0;
            
            // Проверяем окрестность 3x3
            for dy in -3..4 {
                for dx in -3..4 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    
                    let px = (x as i32 + dx).max(0).min(width as i32 - 1) as u32;
                    let py = (y as i32 + dy).max(0).min(height as i32 - 1) as u32;
                    
                    let center_val = image.get_pixel(x, y)[0] as f32;
                    let neighbor_val = image.get_pixel(px, py)[0] as f32;
                    
                    sum += (center_val - neighbor_val).abs();
                    count += 1;
                }
            }
            
            let strength = sum / count as f32;
            
            if strength > feature_threshold {
                keypoints.push(KeyPoint { x, y, strength });
            }
        }
    }
    
    debug!("Найдено {} ключевых точек с порогом {}", keypoints.len(), feature_threshold);
    
    // Сортируем по силе и оставляем только сильнейшие точки
    keypoints.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap_or(std::cmp::Ordering::Equal));
    keypoints.truncate(500); // Ограничиваем количество точек
    
    debug!("После сортировки и ограничения: {} точек", keypoints.len());
    
    keypoints
}
/// Вычисляет дескриптор для ключевой точки с указанным размером
fn compute_descriptor_with_params(image: &GrayImage, x: u32, y: u32, descriptor_size: usize) -> Descriptor {
    let mut descriptor = Vec::new();
    
    // Вычисляем размер окна на основе размера дескриптора
    let window_size = (descriptor_size as f32).sqrt() as i32;
    let half_window = window_size / 2;
    
    for dy in -half_window..=half_window {
        for dx in -half_window..=half_window {
            let px = (x as i32 + dx).max(0).min(image.width() as i32 - 1) as u32;
            let py = (y as i32 + dy).max(0).min(image.height() as i32 - 1) as u32;
            
            let pixel_value = image.get_pixel(px, py)[0];
            descriptor.push(pixel_value);
            
            if descriptor.len() >= descriptor_size {
                break;
            }
        }
        if descriptor.len() >= descriptor_size {
            break;
        }
    }
    
    // Если дескриптор слишком маленький, дополняем нулями
    while descriptor.len() < descriptor_size {
        descriptor.push(0);
    }
    
    debug!("Вычислен дескриптор для точки ({}, {}), размер: {}", x, y, descriptor.len());
    
    Descriptor { data: descriptor }
}
/// Ищет совпадения между дескрипторами с использованием динамического порога
fn find_matches_with_params(template_descriptors: &[Descriptor], screen_descriptors: &[Descriptor], match_threshold: f32) -> Vec<Match> {
    let mut matches = Vec::new();
    
    debug!("Поиск совпадений между {} шаблонными и {} экранными дескрипторами с порогом {}", 
           template_descriptors.len(), screen_descriptors.len(), match_threshold);
    
    for (template_idx, template_desc) in template_descriptors.iter().enumerate() {
        let mut best_distance = f32::MAX;
        let mut best_screen_idx = 0;
        
        for (screen_idx, screen_desc) in screen_descriptors.iter().enumerate() {
            let distance = compute_descriptor_distance(template_desc, screen_desc);
            
            if distance < best_distance {
                best_distance = distance;
                best_screen_idx = screen_idx;
            }
        }
        
        if best_distance < match_threshold {
            matches.push(Match {
                template_idx,
                screen_idx: best_screen_idx,
                distance: best_distance,
            });
        }
    }
    
    debug!("Найдено {} совпадений с порогом {}", matches.len(), match_threshold);
    
    matches
}
/// Вычисляет расстояние между дескрипторами
fn compute_descriptor_distance(desc1: &Descriptor, desc2: &Descriptor) -> f32 {
    let mut sum = 0.0;
    
    // Проверяем, что дескрипторы одинакового размера
    if desc1.data.len() != desc2.data.len() {
        error!("Размеры дескрипторов не совпадают: {} != {}", desc1.data.len(), desc2.data.len());
        return f32::MAX;
    }
    
    for i in 0..desc1.data.len() {
        let diff = desc1.data[i] as f32 - desc2.data[i] as f32;
        sum += diff * diff;
    }
    
    let distance = (sum / desc1.data.len() as f32).sqrt();
    debug!("Расстояние между дескрипторами: {:.3}", distance);
    
    distance
}
/// Находит наиболее частую X-координату
fn find_most_common_x(coords: &[f32]) -> Option<u32> {
    if coords.is_empty() {
        return None;
    }
    
    info!("Анализ {} X-координат для определения центра колонки", coords.len());
    
    // Округляем координаты до ближайших 10 пикселей
    let rounded: Vec<u32> = coords.iter()
        .map(|&x| (x / 10.0).round() as u32 * 10)
        .collect();
    
    // Считаем частоту
    let mut counts = HashMap::new();
    for &x in &rounded {
        *counts.entry(x).or_insert(0) += 1;
    }
    
    // Выводим статистику для отладки
    info!("Распределение X-координат:");
    let mut count_vec: Vec<_> = counts.iter().collect();
    count_vec.sort_by(|a, b| b.1.cmp(a.1));
    
    for (i, (x, count)) in count_vec.iter().take(5).enumerate() {
        info!("  {}. X={} - {} раз", i + 1, x, count);
    }
    
    // Находим наиболее частую
    counts.into_iter()
        .max_by_key(|&(_, count)| count)
        .map(|(x, _)| x)
}
/// Структура для хранения совпадения
#[derive(Debug)]
struct Match {
    template_idx: usize,
    screen_idx: usize,
    distance: f32,
}