use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use anyhow::Result;
use crate::utils::get_absolute_path_string;

/// Структура для хранения информации о детекции для отладки
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugDetection {
    pub name: String,
    pub similarity: f32,
    pub rect: crate::utils::Rect,
    pub normalized_name: String,
}

/// Структура для хранения отладочной информации
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugSession {
    pub timestamp: String,
    pub total_rois: usize,
    pub detections_above_threshold: Vec<DebugDetection>,
    pub final_detections: Vec<String>,
    pub thresholds: DebugThresholds,
}

/// Пороги для детекции
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugThresholds {
    pub logging_threshold: f32,
    pub decision_threshold: f32,
    pub confirmation_threshold: f32,
}

/// Логгер для сохранения отладочной информации
#[derive(Clone)]
pub struct DebugLogger {
    enabled: bool,
    output_dir: String,
}

impl DebugLogger {
    /// Создает новый экземпляр DebugLogger
    pub fn new(enabled: bool) -> Self {
        let output_dir = get_absolute_path_string("tests/debug_logs");
        if enabled {
            if let Err(e) = fs::create_dir_all(&output_dir) {
                log::error!("Не удалось создать директорию для логов: {}", e);
            }
        }
        
        Self {
            enabled,
            output_dir,
        }
    }
    
    /// Сохраняет отладочную сессию в файл
    pub fn save_session(&self, session: &DebugSession) -> Result<()> {
        if !self.enabled {
            return Ok(());
        }
        
        let filename = format!("session_{}.json", session.timestamp.replace(":", "-"));
        let filepath = Path::new(&self.output_dir).join(filename);
        
        let json_content = serde_json::to_string_pretty(session)?;
        fs::write(&filepath, json_content)?;
        
        log::info!("Отладочная сессия сохранена в: {}", filepath.display());
        Ok(())
    }
    
    /// Логирует все детекции выше порога логирования
    pub fn log_detections_above_threshold(
        &self,
        detections: &[DebugDetection],
        threshold: f32,
        roi_count: usize
    ) {
        if !self.enabled {
            return;
        }
        
        log::info!("=== Все кандидаты DINO (прошедшие порог логирования {:.1}%) ===", threshold * 100.0);
        log::info!("Всего обработано ROI: {}", roi_count);
        
        for (i, detection) in detections.iter().enumerate() {
            log::info!(
                "   Raw DINO {}. '{}' ({}) - Сходство: {:.2}% (ROI: x={}, y={})",
                i + 1,
                detection.name,
                detection.normalized_name,
                detection.similarity * 100.0,
                detection.rect.x,
                detection.rect.y
            );
        }
    }
    
    /// Логирует финальные результаты
    pub fn log_final_results(&self, results: &[String]) {
        if !self.enabled {
            return;
        }
        
        log::info!("=== Финальный результат ({} героев) ===", results.len());
        for (i, hero) in results.iter().enumerate() {
            log::info!("   {}. {}", i + 1, hero);
        }
    }
    
    /// Проверяет, включено ли логирование
    pub fn is_enabled(&self) -> bool {
        self.enabled
    }
}

impl Default for DebugLogger {
    fn default() -> Self {
        Self::new(true) // Включаем по умолчанию для отладки
    }
}

/// Создает новую отладочную сессию
pub fn create_debug_session(
    roi_count: usize,
    detections: &[DebugDetection],
    final_results: &[String],
    thresholds: DebugThresholds,
) -> DebugSession {
    use chrono::Local;
    
    DebugSession {
        timestamp: Local::now().format("%Y-%m-%d_%H-%M-%S").to_string(),
        total_rois: roi_count,
        detections_above_threshold: detections.to_vec(),
        final_detections: final_results.to_vec(),
        thresholds,
    }
}

/// Нормализует имя героя (аналог normalize_hero_name из Python)
pub fn normalize_hero_name(name: &str) -> String {
    if name.is_empty() {
        return String::new();
    }
    
    let mut normalized = name.to_lowercase();
    
    // Удаляем числовые суффиксы типа _1, _2, _v2, _v3 и т.д.
    normalized = regex::Regex::new(r"[_ ]*v\d+$").unwrap().replace(&normalized, "").to_string();
    normalized = regex::Regex::new(r"_\d+$").unwrap().replace(&normalized, "").to_string();
    
    // Удаляем другие общие суффиксы
    let suffixes_to_remove = ["_icon", "_template", "_small", "_left", "_right", "_horizontal", "_adv", "_padded"];
    for suffix in suffixes_to_remove {
        if normalized.ends_with(suffix) {
            normalized = normalized[..normalized.len() - suffix.len()].to_string();
        }
    }
    
    // Заменяем тире, подчеркивания на пробелы, убираем лишние пробелы
    normalized = regex::Regex::new(r"[-_]+").unwrap().replace(&normalized, " ").to_string();
    normalized = regex::Regex::new(r"\s+").unwrap().replace(&normalized, " ").trim().to_string();
    
    // TODO: Здесь можно добавить поиск канонического имени в базе данных героев
    // Пока просто возвращаем капитализированную версию
    
    // Капитализируем слова
    let parts: Vec<&str> = normalized.split(' ').collect();
    let capitalized: Vec<String> = parts
        .iter()
        .filter(|p| !p.is_empty())
        .map(|p| {
            let mut chars = p.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().chain(chars).collect(),
            }
        })
        .collect();
    
    let result = capitalized.join(" ");
    
    if result != name {
        log::debug!("Нормализовано имя: '{}' -> '{}'", name, result);
    }
    
    result
}