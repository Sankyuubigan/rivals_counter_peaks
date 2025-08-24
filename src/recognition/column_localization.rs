//! Локализация колонки героев с помощью настоящей AKAZE через чистый Rust
//!
//! Этот модуль использует настоящую реализацию AKAZE на чистом Rust
//! для детектирования и распознавания героев на изображениях скриншотов.

use anyhow::Result;
use image::{DynamicImage, GrayImage};
use imageproc::contrast::equalize_histogram;
use std::collections::HashMap;
use std::path::Path;
use crate::utils::get_absolute_path_string;
use log::{info, warn, debug, error};
use crate::recognition::akaze_analysis;
use crate::recognition::akaze_opencv;

/// Структура для хранения результатов локализации колонки
#[derive(Debug, Clone)]
pub struct ColumnLocalizationResult {
    pub column_x_center: Option<u32>,
    pub detected_heroes: Vec<String>,
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
    info!("  Макс. соотношение расстояний: {:.2}", akaze_params.max_distance_ratio);
    info!("  Мин. героев: {}", localization_params.min_heroes_for_column);

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

    // Улучшаем контраст изображения
    let gray_image = image.to_luma8();
    let enhanced_image = equalize_histogram(&gray_image);
    info!("Изображение улучшено: {}x{}", enhanced_image.width(), enhanced_image.height());

    // Конвертируем в DynamicImage для AKAZE
    let enhanced_dynamic = DynamicImage::ImageLuma8(enhanced_image);

    // Ищем героев с помощью AKAZE
    let detected_heroes = akaze_opencv::find_heroes_akaze(
        &enhanced_dynamic,
        &hero_templates,
        &akaze_params
    ).unwrap_or_else(|e| {
        error!("Ошибка при поиске героев с AKAZE: {}", e);
        Vec::new()
    });

    info!("AKAZE нашел {} героев: {:?}", detected_heroes.len(), detected_heroes);

    if detected_heroes.is_empty() {
        warn!("НИ ОДНОГО ГЕРОЯ НЕ БЫЛО РАСПОЗНАНО С AKAZE!");
        info!("Возможные причины:");
        info!("1. Слишком строгие параметры AKAZE");
        info!("2. Проблемы с качеством шаблонов");
        info!("3. Сложные условия освещения на скриншоте");

        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
        });
    }

    if detected_heroes.len() < localization_params.min_heroes_for_column {
        warn!("Недостаточно героев для надежной локализации колонки: {} < {}",
              detected_heroes.len(), localization_params.min_heroes_for_column);
        return Ok(ColumnLocalizationResult {
            column_x_center: None,
            detected_heroes,
        });
    }

    // TODO: Определение центра колонки на основе найденных героев
    // Пока что возвращаем None, так как для этого нужна дополнительная логика
    warn!("Определение центра колонки пока не реализовано для новой AKAZE");

    Ok(ColumnLocalizationResult {
        column_x_center: None, // TODO: реализовать определение центра
        detected_heroes,
    })
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