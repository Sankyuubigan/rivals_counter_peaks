use iced::widget::image;
use log::{info, warn};
use std::collections::HashMap;
use crate::utils;
use std::fs;

/// Преобразует имя героя (например, "Peni Parker", "Cloak & Dagger")
/// в стандартизированный *базовый* префикс имени файла (например, "peni_parker", "cloak_and_dagger").
fn hero_name_to_base_filename(name: &str) -> String {
    name.to_lowercase()
        .replace(" & ", "_and_") // Сначала обработать особые случаи
        .replace([' ', '.'], "_") // Затем общие разделители
        .replace("__", "_") // Очистка двойных подчёркиваний
}

// Загружает иконки героев в формате, понятном для Iced.
pub fn load_hero_icons(
    hero_names: &[String],
) -> HashMap<String, image::Handle> {
    info!("Загрузка иконок героев для Iced...");
    let mut icons = HashMap::new();
    let icons_dir = utils::get_project_root().join("resources").join("heroes_icons");

    if !icons_dir.exists() {
        warn!("Директория с иконками не найдена по пути: {}", icons_dir.display());
        return icons;
    }

    // Получаем список всех файлов в директории один раз для эффективности
    let all_icon_files: Vec<_> = fs::read_dir(&icons_dir)
        .unwrap()
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let path = entry.path();
            if path.is_file() {
                path.file_name().and_then(|name| name.to_str().map(String::from))
            } else {
                None
            }
        })
        .collect();

    for hero_name in hero_names {
        // РЕШЕНИЕ ПРОБЛЕМЫ С ИМЕНАМИ:
        // 1. Преобразуем имя героя в базовое имя файла (например, "Peni Parker" -> "peni_parker")
        let base_filename = hero_name_to_base_filename(hero_name);
        
        // 2. Ищем в списке файлов первый, который начинается с этого базового имени
        let found_icon_filename = all_icon_files.iter().find(|&filename| filename.starts_with(&base_filename));

        if let Some(icon_filename) = found_icon_filename {
            let icon_path = icons_dir.join(icon_filename);
            // Создаем `Handle` из пути к файлу. Iced загрузит его, когда потребуется.
            let handle = image::Handle::from_path(icon_path);
            icons.insert(hero_name.clone(), handle);
        } else {
            // Для отладки оставляем предупреждение, если иконка всё же не найдена
            warn!("Иконка для героя '{}' не найдена (базовое имя для поиска: '{}')", hero_name, base_filename);
        }
    }
    info!("Загружено {} иконок.", icons.len());
    icons
}