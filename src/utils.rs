use std::path::PathBuf;
use std::env;
use ndarray::ArrayView1;
use serde::{Serialize, Deserialize};

/// Простая структура для представления прямоугольной области.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize)]
pub struct Rect {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
}

impl Rect {
    /// Вычисляет площадь пересечения двух прямоугольников.
    pub fn intersection_area(&self, other: &Rect) -> u32 {
        let x_overlap = (self.x + self.width).min(other.x + other.width) as i64
            - self.x.max(other.x) as i64;
        let y_overlap = (self.y + self.height).min(other.y + other.height) as i64
            - self.y.max(other.y) as i64;
        if x_overlap > 0 && y_overlap > 0 {
            (x_overlap * y_overlap) as u32
        } else {
            0
        }
    }
    
    /// Вычисляет "пересечение над объединением" (Intersection over Union - IoU).
    pub fn iou(&self, other: &Rect) -> f32 {
        let intersection_area = self.intersection_area(other);
        if intersection_area == 0 {
            return 0.0;
        }
        let self_area = self.width * self.height;
        let other_area = other.width * other.height;
        let union_area = self_area + other_area - intersection_area;
        if union_area == 0 {
            0.0
        } else {
            intersection_area as f32 / union_area as f32
        }
    }
}

/// Вычисляет косинусное сходство между двумя векторами.
pub fn cosine_similarity(a: ArrayView1<f32>, b: ArrayView1<f32>) -> f32 {
    let dot_product = a.dot(&b);
    let norm_a = a.dot(&a).sqrt();
    let norm_b = b.dot(&b).sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        0.0
    } else {
        dot_product / (norm_a * norm_b)
    }
}

/// Получает путь к корню проекта относительно исполняемого файла
pub fn get_project_root() -> PathBuf {
    // Получаем путь к текущей рабочей директории
    if let Ok(cwd) = env::current_dir() {
        // Проверяем, содержит ли путь "src" или "target"
        let mut path = cwd.clone();
        
        // Если мы находимся в директории src или target, поднимаемся на уровень выше
        if path.ends_with("src") || path.ends_with("target") {
            if let Some(parent) = path.parent() {
                path = parent.to_path_buf();
            }
        }
        
        // Если мы находимся в директории release или debug, поднимаемся на два уровня выше
        if path.ends_with("release") || path.ends_with("debug") {
            if let Some(parent) = path.parent() {
                path = parent.to_path_buf();
                if let Some(grandparent) = path.parent() {
                    path = grandparent.to_path_buf();
                }
            }
        }
        
        // Проверяем наличие файла Cargo.toml для подтверждения, что это корень проекта
        if path.join("Cargo.toml").exists() {
            return path;
        }
        
        // Если не нашли, ищем директорию с Cargo.toml вверх по иерархии
        let mut search_path = cwd;
        while let Some(parent) = search_path.parent() {
            if parent.join("Cargo.toml").exists() {
                return parent.to_path_buf();
            }
            search_path = parent.to_path_buf();
        }
    }
    
    // Если не удалось определить, возвращаем текущую директорию
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

/// Формирует абсолютный путь к файлу относительно корня проекта
pub fn get_absolute_path(relative_path: &str) -> PathBuf {
    let mut root = get_project_root();
    root.push(relative_path);
    root
}

/// Проверяет существование файла по указанному относительному пути
pub fn file_exists(relative_path: &str) -> bool {
    get_absolute_path(relative_path).exists()
}

/// Возвращает строковое представление абсолютного пути для логирования
pub fn get_absolute_path_string(relative_path: &str) -> String {
    get_absolute_path(relative_path).to_string_lossy().to_string()
}

/// Нормализует имя героя для сравнения (аналог normalize_hero_name из Python)
pub fn normalize_hero_name(name: &str) -> String {
    // Сначала удаляем числовые суффиксы после подчеркивания (_1, _2, _3 и т.д.)
    let cleaned_name = if let Some(pos) = name.rfind('_') {
        let suffix = &name[pos + 1..];
        if suffix.chars().all(|c| c.is_ascii_digit()) {
            &name[..pos]
        } else {
            name
        }
    } else {
        name
    };

    let result = cleaned_name.to_lowercase()
        .replace('_', " ")
        .replace('&', "and")
        .split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str().to_lowercase().as_str(),
            }
        })
        .collect::<Vec<String>>()
        .join(" ");

    // Отладочная информация
    println!("normalize_hero_name: '{}' -> '{}' -> '{}'", name, cleaned_name, result);

    result
}