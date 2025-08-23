//! Анализ и сравнение реализации AKAZE с Python-версией
//! 
//! Этот модуль содержит анализ различий между реализацией AKAZE
//! в Rust и Python версиями, а также рекомендации по улучшению.

use log::{info, warn, debug, error};

/// Структура для хранения параметров AKAZE
pub struct AkazeParams {
    pub feature_threshold: f32,
    pub match_threshold: f32,
    pub min_match_count: usize,
    pub descriptor_size: usize,
    pub min_heroes_for_column: usize,
}

/// Параметры из Python-версии
pub const PYTHON_AKAZE_PARAMS: AkazeParams = AkazeParams {
    feature_threshold: 30.0,      // В Python был другой порог
    match_threshold: 0.8,         // В Python был другой порог сопоставления
    min_match_count: 3,           // В Python требовалось меньше совпадений
    descriptor_size: 64,         // В Python дескрипторы были больше
    min_heroes_for_column: 1,     // В Python требовался минимум 1 герой
};

/// Текущие параметры в Rust
pub const RUST_AKAZE_PARAMS: AkazeParams = AkazeParams {
    feature_threshold: 50.0,
    match_threshold: 0.7,
    min_match_count: 5,
    descriptor_size: 8,
    min_heroes_for_column: 2,
};

/// Анализ различий между реализациями
pub fn analyze_differences() {
    info!("=== АНАЛИЗ РАЗЛИЧИЙ AKAZE: RUST vs PYTHON ===");
    
    info!("1. Порог силы особенности:");
    info!("   Python: {:.1}", PYTHON_AKAZE_PARAMS.feature_threshold);
    info!("   Rust:   {:.1}", RUST_AKAZE_PARAMS.feature_threshold);
    info!("   Разница: {:.1} (Rust порог выше)", 
          RUST_AKAZE_PARAMS.feature_threshold - PYTHON_AKAZE_PARAMS.feature_threshold);
    
    info!("2. Порог сопоставления дескрипторов:");
    info!("   Python: {:.1}", PYTHON_AKAZE_PARAMS.match_threshold);
    info!("   Rust:   {:.1}", RUST_AKAZE_PARAMS.match_threshold);
    info!("   Разница: {:.1} (Rust порог ниже)", 
          RUST_AKAZE_PARAMS.match_threshold - PYTHON_AKAZE_PARAMS.match_threshold);
    
    info!("3. Минимальное количество совпадений:");
    info!("   Python: {}", PYTHON_AKAZE_PARAMS.min_match_count);
    info!("   Rust:   {}", RUST_AKAZE_PARAMS.min_match_count);
    info!("   Разница: {} (Rust требует больше совпадений)", 
          RUST_AKAZE_PARAMS.min_match_count - PYTHON_AKAZE_PARAMS.min_match_count);
    
    info!("4. Размер дескриптора:");
    info!("   Python: {}", PYTHON_AKAZE_PARAMS.descriptor_size);
    info!("   Rust:   {}", RUST_AKAZE_PARAMS.descriptor_size);
    info!("   Разница: {} (Rust дескрипторы значительно меньше)", 
          PYTHON_AKAZE_PARAMS.descriptor_size - RUST_AKAZE_PARAMS.descriptor_size);
    
    info!("5. Минимальное количество героев для колонки:");
    info!("   Python: {}", PYTHON_AKAZE_PARAMS.min_heroes_for_column);
    info!("   Rust:   {}", RUST_AKAZE_PARAMS.min_heroes_for_column);
    info!("   Разница: {} (Rust требует больше героев)", 
          RUST_AKAZE_PARAMS.min_heroes_for_column - PYTHON_AKAZE_PARAMS.min_heroes_for_column);
    
    info!("");
    info!("=== ВЫВОДЫ И РЕКОМЕНДАЦИИ ===");
    
    warn!("ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ РАЗЛИЧИЯ:");
    warn!("1. Размер дескриптора в Rust (8) значительно меньше, чем в Python (64)");
    warn!("   Это приводит к низкой точности сопоставления!");
    
    warn!("2. Порог силы особенности в Rust (50) выше, чем в Python (30)");
    warn!("   Это приводит к пропуску слабых, но потенциально важных особенностей");
    
    warn!("3. Требуется больше совпадений в Rust (5) vs Python (3)");
    warn!("   Это делает систему более строгой, но может приводить к пропускам");
    
    info!("");
    info!("РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:");
    info!("1. Увеличить размер дескриптора до 64 (как в Python)");
    info!("2. Снизить порог силы особенности до 30-40");
    info!("3. Снизить минимальное количество совпадений до 3-4");
    info!("4. Рассмотреть возможность использования настоящей реализации AKAZE");
    info!("5. Добавить нормализацию дескрипторов");
    info!("6. Улучшить алгоритм сопоставления с использованием FLANN или подобного");
}

/// Рекомендуемые параметры для улучшения работы AKAZE
pub const RECOMMENDED_AKAZE_PARAMS: AkazeParams = AkazeParams {
    feature_threshold: 35.0,      // Сниженный порог
    match_threshold: 0.75,        // Компромиссный порог
    min_match_count: 3,           // Сниженное требование
    descriptor_size: 64,         // Увеличенный размер (как в Python)
    min_heroes_for_column: 1,     // Сниженное требование
};

/// Применяет рекомендуемые параметры (без рекурсивного вызова анализа)
pub fn get_recommended_params() -> AkazeParams {
    RECOMMENDED_AKAZE_PARAMS
}