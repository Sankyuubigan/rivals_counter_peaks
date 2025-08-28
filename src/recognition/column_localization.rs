//! Локализация колонки героев с помощью настоящей AKAZE через чистый Rust
//!
//! Этот модуль использует настоящую реализацию AKAZE на чистом Rust
//! для детектирования и распознавания героев на изображениях скриншотов.

use crate::recognition::akaze_analysis;
use crate::recognition::akaze_opencv;
use crate::utils::get_absolute_path_string;
use anyhow::Result;
use image::{DynamicImage, GrayImage};
use imageproc::contrast::equalize_histogram;
use log::{debug, error, info, warn};
use std::collections::HashMap;
use std::path::Path;

/// Структура для хранения результатов локализации колонки
#[derive(Debug, Clone)]
pub struct ColumnLocalizationResult {
    pub column_x_center: Option<u32>,
    pub detected_heroes: Vec<String>,
    pub hero_positions: Vec<HeroPosition>,
}

/// Структура для хранения позиции героя
#[derive(Debug, Clone)]
pub struct HeroPosition {
    pub name: String,
    pub x: u32,
    pub y: u32,
    pub match_count: usize,
}

/// Параметры для локализации колонки (отдельные от AKAZE параметров)
#[derive(Debug, Clone)]
pub struct LocalizationParams {
    pub min_heroes_for_column: usize,
}

impl Default for LocalizationParams {
    fn default() -> Self {
        Self {
            min_heroes_for_column: 2,
        }
    }
}

/// Локализует колонку с героями с помощью настоящей AKAZE на чистом Rust
pub fn localize_hero_column(image: &DynamicImage) -> Result<ColumnLocalizationResult> {
    info!("=== НАЧАЛО ЛОКАЛИЗАЦИИ КОЛОНКИ (AKAZE на чистом Rust) ===");

    // Получаем параметры AKAZE
    let akaze_params = akaze_analysis::get_akaze_params();
    let localization_params = LocalizationParams::default();

    info!("Используемые параметры AKAZE:");
    info!("  Мин. совпадений: {}", akaze_params.min_match_count);
    info!(
        "  Макс. соотношение расстояний: {:.2}",
        akaze_params.max_distance_ratio
    );
    info!(
        "  Мин. героев: {}",
        localization_params.min_heroes_for_column
    );

    // Загружаем шаблоны героев
    info!("Начало загрузки шаблонов героев...");
    let hero_templates = load_hero_templates()?;

    if hero_templates.is_empty() {
        error!("Словарь шаблонов пуст. Локализация колонки невозможна.");
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes: Vec::new(),
            hero_positions: Vec::new(),
        });
    }

    info!("Загружено шаблонов для {} героев", hero_templates.len());
    for (hero_name, templates) in &hero_templates {
        info!("  - {}: {} шаблон(ов)", hero_name, templates.len());
        for (i, template) in templates.iter().enumerate() {
            info!(
                "    Шаблон #{}: {}x{}",
                i + 1,
                template.width(),
                template.height()
            );
        }
    }

    // Улучшаем контраст изображения
    let gray_image = image.to_luma8();
    let enhanced_image = equalize_histogram(&gray_image);
    info!(
        "Изображение улучшено: {}x{}",
        enhanced_image.width(),
        enhanced_image.height()
    );

    // Конвертируем в DynamicImage для AKAZE
    let enhanced_dynamic = DynamicImage::ImageLuma8(enhanced_image);

    // Сначала пробуем template matching (более надежный для иконок)
    let template_results = akaze_opencv::find_heroes_template_matching(
        &enhanced_dynamic,
        &hero_templates,
        &hero_templates.keys().cloned().collect::<Vec<String>>(),
        0.7, // порог similarity
    ).unwrap_or_else(|e| {
        error!("Ошибка при template matching: {}", e);
        Vec::new()
    });

    // Конвертируем результаты template matching в HeroDetectionResult
    let mut hero_positions: Vec<akaze_opencv::HeroDetectionResult> = template_results.into_iter()
        .map(|tm| akaze_opencv::HeroDetectionResult {
            hero_name: tm.hero_name,
            match_count: 1, // template matching всегда дает 1 совпадение
            avg_distance: 1.0 - tm.similarity, // конвертируем similarity в distance
            center_x: tm.center_x,
            center_y: tm.center_y,
            width: tm.width,
            height: tm.height,
        })
        .collect();

    // Если template matching не нашел героев, используем AKAZE как fallback
    if hero_positions.is_empty() {
        warn!("Template matching не нашел героев, используем AKAZE как fallback");
        hero_positions = akaze_opencv::find_hero_positions_akaze(
            &enhanced_dynamic,
            &hero_templates,
            &hero_templates.keys().cloned().collect::<Vec<String>>(),
            &akaze_params
        ).unwrap_or_else(|e| {
            error!("Ошибка при поиске позиций героев с AKAZE: {}", e);
            Vec::new()
        });
    }

    info!(
        "AKAZE нашел {} позиций героев",
        hero_positions.len()
    );

    // Извлекаем имена героев из позиций
    let detected_heroes: Vec<String> = hero_positions.iter()
        .map(|pos| pos.hero_name.clone())
        .collect();

    if detected_heroes.is_empty() {
        warn!("НИ ОДНОГО ГЕРОЯ НЕ БЫЛО РАСПОЗНАНО С AKAZE!");
        info!("Возможные причины:");
        info!("1. Слишком строгие параметры AKAZE");
        info!("2. Проблемы с качеством шаблонов");
        info!("3. Сложные условия освещения на скриншоте");

        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
            hero_positions: Vec::new(),
        });
    }

    if detected_heroes.len() < localization_params.min_heroes_for_column {
        warn!(
            "Недостаточно героев для надежной локализации колонки: {} < {}",
            detected_heroes.len(),
            localization_params.min_heroes_for_column
        );
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
            hero_positions: Vec::new(),
        });
    }

    // Определяем центр колонки на основе найденных позиций героев
    // Аналогично Python версии: собираем все X координаты и вычисляем медиану
    let mut x_coords: Vec<u32> = Vec::new();

    for pos in &hero_positions {
        // Для каждого героя добавляем его центральную X координату
        // В Python версии используется WINDOW_SIZE_W_DINO = 95
        let roi_half_width = 95 / 2;
        let roi_left_x = pos.center_x.saturating_sub(roi_half_width);
        let roi_right_x = pos.center_x.saturating_add(roi_half_width);

        // Добавляем координаты из области героя
        x_coords.push(roi_left_x);
        x_coords.push(pos.center_x);
        x_coords.push(roi_right_x);

        info!("Герой {} в позиции x={}, добавлены координаты {}, {}, {}",
              pos.hero_name, pos.center_x, roi_left_x, pos.center_x, roi_right_x);
    }

    // Вычисляем медиану X координат (аналогично Python версии)
    x_coords.sort();
    let median_x = if x_coords.is_empty() {
        warn!("Не удалось собрать X координаты для определения центра колонки");
        None
    } else {
        let mid = x_coords.len() / 2;
        if x_coords.len() % 2 == 0 {
            Some((x_coords[mid - 1] + x_coords[mid]) / 2)
        } else {
            Some(x_coords[mid])
        }
    };

    if let Some(center_x) = median_x {
        info!("Определен центр колонки X = {} на основе {} координат", center_x, x_coords.len());

        // Конвертируем hero_positions в HeroPosition структуры
        let converted_positions: Vec<HeroPosition> = hero_positions.into_iter()
            .map(|pos| HeroPosition {
                name: pos.hero_name,
                x: pos.center_x,
                y: pos.center_y,
                match_count: pos.match_count,
            })
            .collect();

        Ok(ColumnLocalizationResult {
            column_x_center: Some(center_x),
            detected_heroes,
            hero_positions: converted_positions,
        })
    } else {
        warn!("Не удалось определить центр колонки");
        Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
            hero_positions: Vec::new(),
        })
    }
}

/// Загружает шаблоны героев
pub fn load_hero_templates() -> Result<HashMap<String, Vec<GrayImage>>> {
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
                    let hero_name = parts[0..parts.len() - 1].join("_");
                    let extension = path.extension().and_then(|s| s.to_str()).unwrap_or("");

                    info!("  Определенное имя героя: '{}'", hero_name);
                    info!("  Расширение файла: '{}'", extension);

                    if extension == "png" || extension == "jpg" || extension == "jpeg" {
                        match image::open(&path) {
                            Ok(img) => {
                                let gray_img = img.to_luma8();
                                templates
                                    .entry(hero_name)
                                    .or_insert_with(Vec::new)
                                    .push(gray_img);
                                loaded_count += 1;
                                info!(
                                    "  ✓ Шаблон успешно загружен: {}x{}",
                                    img.width(),
                                    img.height()
                                );
                            }
                            Err(e) => {
                                error!(
                                    "  ✗ Не удалось загрузить изображение '{}': {}",
                                    file_name, e
                                );
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
