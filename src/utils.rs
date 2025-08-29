use std::path::{Path, PathBuf};
use std::env;
use ndarray::ArrayView1;

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
    if let Ok(cwd) = env::current_dir() {
        if path_is_project_root(&cwd) {
            return cwd;
        }
        
        let mut current = cwd.as_path();
        while let Some(parent) = current.parent() {
            if path_is_project_root(parent) {
                return parent.to_path_buf();
            }
            current = parent;
        }
    }
    
    // Если не удалось определить, возвращаем текущую директорию
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn path_is_project_root(path: &Path) -> bool {
    path.join("Cargo.toml").exists() && path.join("src").is_dir()
}


/// Формирует абсолютный путь к файлу относительно корня проекта
pub fn get_absolute_path(relative_path: &str) -> PathBuf {
    get_project_root().join(relative_path)
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
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
            }
        })
        .collect::<Vec<String>>()
        .join(" ");

    result
}