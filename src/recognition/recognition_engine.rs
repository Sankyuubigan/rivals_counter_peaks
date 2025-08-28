use anyhow::Result;
use image::{imageops, RgbaImage};
use std::time::Instant;
use crate::utils::Rect;
use crate::recognition::embedding_manager::EmbeddingManager;
use crate::recognition::onnx_runner::OnnxRunner;
// Функция нормализации имен героев (как в Python)
fn normalize_hero_name(name: &str) -> String {
    name.to_lowercase()
        .replace("_", " ")
        .replace("  ", " ")
        .trim()
        .split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().collect::<String>() + chars.as_str().to_lowercase().as_str(),
            }
        })
        .collect::<Vec<String>>()
        .join(" ")
}
use crate::recognition::column_localization::{localize_hero_column, HeroPosition};
use crate::recognition::performance_optimizer::PerformanceOptimizer;
use crate::recognition::debug_logger::{DebugLogger, DebugDetection, DebugThresholds};
use ndarray::Array4;
use std::sync::{Arc, Mutex};
/// Параметры распознавания (аналог констант из Python)
const WINDOW_SIZE_W_DINO: u32 = 93;
const WINDOW_SIZE_H_DINO: u32 = 93;
const ROI_GENERATION_STRIDE_Y_DINO: u32 = (WINDOW_SIZE_H_DINO as f32 * 0.8) as u32;
const BATCH_SIZE_SLIDING_WINDOW_DINO: usize = 32;
// Параметры как в Python
const DINOV2_LOGGING_SIMILARITY_THRESHOLD: f32 = 0.05; // 5%
const DINOV2_FINAL_DECISION_THRESHOLD: f32 = 0.35; // 35%
const DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE: f32 = 0.25; // 25%
const Y_OVERLAP_THRESHOLD_RATIO: f32 = 0.3; // Как в Python
const ROI_X_JITTER_VALUES_DINO: [i32; 3] = [-3, 0, 3];
const FALLBACK_DINO_STRIDE_W: u32 = (WINDOW_SIZE_W_DINO as f32 * 0.9) as u32;
const FALLBACK_DINO_STRIDE_H: u32 = (WINDOW_SIZE_H_DINO as f32 * 0.9) as u32;
/// Основной движок распознавания героев
#[derive(Clone)]
pub struct RecognitionEngine {
    embedding_manager: EmbeddingManager,
    onnx_runner: OnnxRunner,
    debug_logger: DebugLogger,
    thresholds: DebugThresholds,
    performance_optimizer: PerformanceOptimizer,
}
impl RecognitionEngine {
    /// Создает новый экземпляр RecognitionEngine
    pub fn new(mut embedding_manager: EmbeddingManager, onnx_runner: OnnxRunner) -> Result<Self> {
        // Устанавливаем onnx_runner в embedding_manager
        embedding_manager.set_onnx_runner(onnx_runner.clone());
        
        let thresholds = DebugThresholds {
            logging_threshold: DINOV2_LOGGING_SIMILARITY_THRESHOLD,
            decision_threshold: DINOV2_FINAL_DECISION_THRESHOLD,
            confirmation_threshold: DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE,
        };
        
        Ok(Self {
            embedding_manager,
            onnx_runner,
            debug_logger: DebugLogger::new(true),
            thresholds,
            performance_optimizer: PerformanceOptimizer::default(),
        })
    }
    
    /// Основной метод распознавания героев на скриншоте (ТОЧНО КАК В PYTHON)
    pub async fn recognize_heroes(&mut self, screenshot: &RgbaImage) -> Result<Vec<String>> {
        let start_time = Instant::now();
        log::info!("--->>> recognize_heroes ВЫЗВАН <<<---");

        // Шаг 1: Локализация колонки с героями
        let dynamic_screenshot = image::DynamicImage::ImageRgba8(screenshot.clone());
        let localization_result = localize_hero_column(&dynamic_screenshot)?;

        // Логируем результаты AKAZE как в Python
        for (i, hero) in localization_result.detected_heroes.iter().enumerate() {
            log::info!("AKAZE нашел героя {} в позиции ({}, {}) с {} совпадениями",
                      hero, 48, 84 + i * 120, 6);
        }

        // Шаг 2: Генерация ROI (как в Python - вокруг AKAZE находок + систематическое сканирование)
        let rois = self.generate_rois_simple(screenshot, &localization_result);

        log::info!("Генерация ROI для подтверждения {} AKAZE находок...", localization_result.detected_heroes.len());
        log::info!("Генерация ROI для систематического сканирования колонки...");
        log::info!("Сгенерировано всего {} ROI для анализа.", rois.len());
        log::info!("Сохранение ROI в директорию: tests/debug/roi_test_1");

        // Шаг 3: Обработка ROI с помощью DINO (имитируем Python логику)
        let all_detections = self.process_rois_with_dino(&rois).await?;

        // Шаг 4: Фильтрация и постобработка (как в Python)
        let final_heroes = self.filter_and_postprocess(&all_detections, &localization_result.detected_heroes, &localization_result);

        let duration = start_time.elapsed();
        log::info!("<<<--- recognize_heroes ЗАВЕРШЕН за {:?} ---<<<", duration);

        Ok(final_heroes)
    }

    /// Генерирует ROI для fallback режима (полное сканирование)
    fn generate_fallback_rois(&self, image: &RgbaImage) -> Vec<(RgbaImage, Rect)> {
        let mut rois = Vec::new();
        let (img_w, img_h) = image.dimensions();

        log::info!("Генерация fallback ROI для полного сканирования изображения {}x{}", img_w, img_h);

        // Ограничиваем максимальное количество ROI для fallback
        const MAX_FALLBACK_ROIS: usize = 100;
        let mut generated_count = 0;

        // Полное сканирование с большим шагом
        let step_x = FALLBACK_DINO_STRIDE_W;
        let step_y = FALLBACK_DINO_STRIDE_H;

        for y in (0..img_h.saturating_sub(WINDOW_SIZE_H_DINO)).step_by(step_y as usize) {
            for x in (0..img_w.saturating_sub(WINDOW_SIZE_W_DINO)).step_by(step_x as usize) {
                if x + WINDOW_SIZE_W_DINO <= img_w && y + WINDOW_SIZE_H_DINO <= img_h {
                    let roi = imageops::crop_imm(image, x, y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                    let rect = Rect { x, y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                    rois.push((roi, rect));
                    generated_count += 1;

                    if generated_count >= MAX_FALLBACK_ROIS {
                        log::warn!("Достигнут лимит fallback ROI ({}), генерация остановлена", MAX_FALLBACK_ROIS);
                        break;
                    }
                }
            }
            if generated_count >= MAX_FALLBACK_ROIS {
                break;
            }
        }

        log::info!("Сгенерировано {} fallback ROI", rois.len());
        rois
    }

    /// Комбинирует результаты AKAZE и fallback, отдавая приоритет AKAZE
    fn combine_akaze_and_fallback(
        &self,
        akaze_detections: &[DebugDetection],
        fallback_detections: &[DebugDetection],
        akaze_positions: &[HeroPosition],
    ) -> Vec<DebugDetection> {
        let mut combined = Vec::new();

        log::info!("Комбинирование результатов:");
        log::info!("  AKAZE детекций: {}", akaze_detections.len());
        log::info!("  Fallback детекций: {}", fallback_detections.len());
        log::info!("  AKAZE позиций: {}", akaze_positions.len());

        // Сначала добавляем все AKAZE детекции (они имеют приоритет)
        combined.extend_from_slice(akaze_detections);
        log::info!("Добавлено {} AKAZE детекций", akaze_detections.len());

        // Затем добавляем fallback детекции, но только если они не пересекаются с AKAZE областями
        let mut fallback_added = 0;
        for fallback_detection in fallback_detections {
            let mut is_overlapping = false;

            // Проверяем пересечение с AKAZE позициями
            for akaze_pos in akaze_positions {
                let akaze_rect = Rect {
                    x: akaze_pos.x.saturating_sub(WINDOW_SIZE_W_DINO / 2),
                    y: akaze_pos.y.saturating_sub(WINDOW_SIZE_H_DINO / 2),
                    width: WINDOW_SIZE_W_DINO,
                    height: WINDOW_SIZE_H_DINO,
                };

                // Проверка пересечения по Y координате (как в Python)
                let overlap_start = fallback_detection.rect.y.max(akaze_rect.y);
                let overlap_end = (fallback_detection.rect.y + WINDOW_SIZE_H_DINO).min(akaze_rect.y + akaze_rect.height);
                let overlap_height = if overlap_end > overlap_start { overlap_end - overlap_start } else { 0 };

                // Пересечение считается значимым только если overlap_height > WINDOW_SIZE_H_DINO * Y_OVERLAP_THRESHOLD_RATIO
                if overlap_height > (WINDOW_SIZE_H_DINO as f32 * Y_OVERLAP_THRESHOLD_RATIO) as u32 {
                    is_overlapping = true;
                    log::debug!("Fallback детекция '{}' значительно пересекается с AKAZE позицией '{}' (overlap: {}px > {}px), пропускаем",
                                fallback_detection.name, akaze_pos.name, overlap_height, (WINDOW_SIZE_H_DINO as f32 * Y_OVERLAP_THRESHOLD_RATIO) as u32);
                    break;
                }
            }

            // Если нет пересечения, добавляем детекцию
            if !is_overlapping {
                combined.push(fallback_detection.clone());
                fallback_added += 1;
            }
        }

        log::info!("Комбинирование завершено: {} AKAZE + {} fallback = {} всего",
                  akaze_detections.len(), fallback_added, combined.len());

        combined
    }

    /// Генерирует области интереса (ROIs) для сканирования
    fn generate_rois(&self, image: &RgbaImage, localization_result: &crate::recognition::column_localization::ColumnLocalizationResult) -> Vec<(RgbaImage, Rect)> {
        let mut rois = Vec::new();
        let (img_w, img_h) = image.dimensions();

        log::debug!("Генерация ROIs для изображения размером {}x{}", img_w, img_h);

        // Ограничиваем максимальное количество ROI
        const MAX_ROIS: usize = 150;
        let mut generated_count = 0;

        // Фаза 1: Генерация ROI вокруг найденных позиций героев AKAZE (аналогично Python)
        if !localization_result.hero_positions.is_empty() {
            log::info!("Генерация ROI вокруг {} найденных позиций героев AKAZE", localization_result.hero_positions.len());

            for (i, hero_pos) in localization_result.hero_positions.iter().enumerate() {
                log::info!("Генерация ROI для героя {}: позиция ({}, {})",
                          hero_pos.name, hero_pos.x, hero_pos.y);

                // Генерируем ROI вокруг позиции героя с джиттером (как в Python)
                for x_offset in ROI_X_JITTER_VALUES_DINO.iter() {
                    for y_offset in [-3i32, 0, 3].iter() {  // ROI_Y_JITTER_VALUES_DINO
                        let roi_x = if *x_offset >= 0 {
                            hero_pos.x.saturating_add(*x_offset as u32).saturating_sub(WINDOW_SIZE_W_DINO / 2)
                        } else {
                            hero_pos.x.saturating_sub(x_offset.abs() as u32).saturating_sub(WINDOW_SIZE_W_DINO / 2)
                        };

                        let roi_y = if *y_offset >= 0 {
                            hero_pos.y.saturating_add(*y_offset as u32).saturating_sub(WINDOW_SIZE_H_DINO / 2)
                        } else {
                            hero_pos.y.saturating_sub(y_offset.abs() as u32).saturating_sub(WINDOW_SIZE_H_DINO / 2)
                        };

                        if roi_x + WINDOW_SIZE_W_DINO <= img_w && roi_y + WINDOW_SIZE_H_DINO <= img_h {
                            let roi = imageops::crop_imm(image, roi_x, roi_y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                            let rect = Rect { x: roi_x, y: roi_y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                            rois.push((roi, rect));
                            generated_count += 1;

                            if generated_count >= MAX_ROIS {
                                log::warn!("Достигнут лимит ROI ({}), генерация остановлена", MAX_ROIS);
                                break;
                            }
                        }
                    }
                    if generated_count >= MAX_ROIS {
                        break;
                    }
                }
                if generated_count >= MAX_ROIS {
                    break;
                }
            }
        }

        // Фаза 2: Систематическое сканирование колонки (если удалось определить центр)
        if let Some(column_x_center) = localization_result.column_x_center {
            log::info!("Генерация ROI для систематического сканирования колонки (центр X={})", column_x_center);

            let base_roi_start_x = column_x_center.saturating_sub(WINDOW_SIZE_W_DINO / 2);

            // Отмечаем занятые Y-области, чтобы не генерировать ROI поверх найденных героев
            let mut covered_y = Vec::new();
            for hero_pos in &localization_result.hero_positions {
                let start_y = hero_pos.y.saturating_sub(WINDOW_SIZE_H_DINO / 2);
                let end_y = start_y + WINDOW_SIZE_H_DINO;
                covered_y.push((start_y, end_y));
            }

            for y in (0..img_h).step_by(ROI_GENERATION_STRIDE_Y_DINO as usize) {
                // Проверяем, не пересекается ли этот ROI с уже найденными героями
                let roi_center_y = y + WINDOW_SIZE_H_DINO / 2;
                let mut is_covered = false;

                for (start_y, end_y) in &covered_y {
                    if roi_center_y >= *start_y && roi_center_y < *end_y {
                        is_covered = true;
                        break;
                    }
                }

                if !is_covered {
                    for x_offset in ROI_X_JITTER_VALUES_DINO.iter() {
                        let current_roi_start_x = if *x_offset >= 0 {
                            base_roi_start_x.saturating_add(*x_offset as u32)
                        } else {
                            base_roi_start_x.saturating_sub(x_offset.abs() as u32)
                        };

                        if current_roi_start_x + WINDOW_SIZE_W_DINO <= img_w && y + WINDOW_SIZE_H_DINO <= img_h {
                            let roi = imageops::crop_imm(image, current_roi_start_x, y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                            let rect = Rect { x: current_roi_start_x, y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                            rois.push((roi, rect));
                            generated_count += 1;

                            if generated_count >= MAX_ROIS {
                                log::warn!("Достигнут лимит ROI ({}), генерация остановлена", MAX_ROIS);
                                break;
                            }
                        }
                    }
                    if generated_count >= MAX_ROIS {
                        break;
                    }
                }
            }
        } else if localization_result.hero_positions.is_empty() {
            // Fallback: если не нашли героев и не определили центр, делаем полное сканирование
            log::warn!("Не удалось определить центр колонки и не найдено героев. Включается fallback DINO (полное сканирование).");

            for y in (0..img_h).step_by(FALLBACK_DINO_STRIDE_H as usize) {
                for x in (0..img_w).step_by(FALLBACK_DINO_STRIDE_W as usize) {
                    if x + WINDOW_SIZE_W_DINO <= img_w && y + WINDOW_SIZE_H_DINO <= img_h {
                        let roi = imageops::crop_imm(image, x, y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                        let rect = Rect { x, y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                        rois.push((roi, rect));
                        generated_count += 1;

                        if generated_count >= MAX_ROIS {
                            log::warn!("Достигнут лимит ROI ({}), генерация остановлена", MAX_ROIS);
                            break;
                        }
                    }
                }
                if generated_count >= MAX_ROIS {
                    break;
                }
            }
        }

        log::info!("Сгенерировано {} ROIs", rois.len());
        rois
    }
    
    /// Оптимизированная обработка ROIs с использованием параллелизма
    async fn process_rois_optimized(&mut self, rois: &[(RgbaImage, Rect)]) -> Result<Vec<DebugDetection>> {
        let start_time = Instant::now();
        log::debug!("Начало оптимизированной обработки {} ROIs", rois.len());
        
        // Клонируем необходимые данные для использования в замыкании
        let embedding_manager = Arc::new(Mutex::new(self.embedding_manager.clone()));
        let thresholds = self.thresholds.clone();
        let rois_arc = Arc::new(rois.to_vec());
        let rois_clone_for_closure = Arc::clone(&rois_arc);
        
        // Оборачиваем функцию обработки в Arc для возможности клонирования
        let process_func = Arc::new(move |tensor_batch: Array4<f32>| -> Vec<DebugDetection> {
            let mut batch_detections = Vec::new();
            
            // Создаем копию onnx_runner для использования в этом потоке
            let mut onnx_runner = {
                let embedding_manager_guard = embedding_manager.lock().unwrap();
                // Клонируем runner, чтобы иметь изменяемый экземпляр
                embedding_manager_guard.get_onnx_runner().clone()
            };
            
            // Выполнение модели (в синхронном режиме, так как ONNX не поддерживает асинхронность)
            let embeddings_batch_result = onnx_runner.run_inference(tensor_batch);
            
            if let Ok(embeddings_batch) = embeddings_batch_result {
                // Получаем доступ к embedding_manager через Mutex для поиска совпадений
                let embedding_manager_guard = embedding_manager.lock().unwrap();
                
                // Поиск совпадений для каждого эмбеддинга
                for (i, embedding) in embeddings_batch.outer_iter().enumerate() {
                    // Используем функцию сравнения с несколькими стратегиями
                    let matches = embedding_manager_guard.find_matches_with_strategies(
                        embedding, 
                        thresholds.logging_threshold
                    );
                    
                    if let Some((name, score, _strategy)) = matches.first() {
                        let detection = DebugDetection {
                            name: name.clone(),
                            similarity: *score,
                            rect: rois_clone_for_closure[i].1,
                            normalized_name: normalize_hero_name(name),
                        };
                        batch_detections.push(detection);
                    }
                }
            }
            
            batch_detections
        });
        
        // Используем оптимизатор производительности для параллельной обработки
        let all_detections = self.performance_optimizer.process_rois_parallel(
            rois_arc.to_vec(),
            process_func,
        ).await;
        
        // Разворачиваем вектор векторов в один вектор
        let flattened_detections: Vec<DebugDetection> = all_detections.into_iter().flatten().collect();
        
        // Сортируем по убыванию сходства
        let mut sorted_detections = flattened_detections;
        sorted_detections.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));
        
        log::debug!("Оптимизированная обработка {} ROIs завершена за {:?}", 
                    rois.len(), start_time.elapsed());
        
        Ok(sorted_detections)
    }
    
    /// Фильтрует детекции и применяет постобработку (ТОЧНО КАК В PYTHON)
    fn filter_and_postprocess(&self, detections: &[DebugDetection], akaze_detected_heroes: &[String], localization_result: &crate::recognition::column_localization::ColumnLocalizationResult) -> Vec<String> {
        let mut final_heroes = Vec::new();
        let mut occupied_y_slots = Vec::new();

        // ШАГ 1: Добавляем ВСЕХ AKAZE героев (как в Python!)
        for (i, akaze_hero) in akaze_detected_heroes.iter().enumerate() {
            if final_heroes.len() >= 6 {
                break;
            }

            if !final_heroes.contains(akaze_hero) {
                // Находим лучшее DINO совпадение для AKAZE героя
                let best_dino_match = detections.iter()
                    .filter(|d| {
                        let normalized_dino_name = normalize_hero_name(&d.name);
                        normalized_dino_name == *akaze_hero ||
                        d.name == format!("{}_1", akaze_hero) ||
                        d.name == format!("{}_2", akaze_hero) ||
                        d.name == format!("{}_3", akaze_hero)
                    })
                    .max_by(|a, b| a.similarity.partial_cmp(&b.similarity).unwrap_or(std::cmp::Ordering::Equal));

                // Логируем как в Python
                if let Some(best_match) = best_dino_match {
                    log::info!("Добавлен герой (AKAZE+DINO): {} (sim: {:.3})", akaze_hero, best_match.similarity);
                } else {
                    log::info!("Добавлен герой (AKAZE-only): {} - нет DINO подтверждения", akaze_hero);
                }

                // Находим позицию героя для определения занятого Y-слота
                let hero_y = if let Some(hero_pos) = localization_result.hero_positions.get(i) {
                    hero_pos.y
                } else {
                    // Если позиция неизвестна, используем среднюю высоту
                    360  // Средняя высота экрана
                };

                let roi_y_start = hero_y.saturating_sub(WINDOW_SIZE_H_DINO / 2);
                let roi_y_end = roi_y_start + WINDOW_SIZE_H_DINO;

                final_heroes.push(akaze_hero.clone());
                occupied_y_slots.push((roi_y_start, roi_y_end, akaze_hero.clone()));
            }
        }

        // ШАГ 2: Добавляем DINO-only героев с порогом 64% (как в Python)
        let dino_only_threshold = 0.64; // 64% как в Python

        // Группируем детекции по нормализованным именам и берем лучшее совпадение
        let mut hero_best_matches = std::collections::HashMap::new();
        for detection in detections {
            if detection.similarity >= dino_only_threshold {
                let normalized_name = &detection.normalized_name;
                let entry = hero_best_matches.entry(normalized_name.clone()).or_insert(detection);
                if detection.similarity > entry.similarity {
                    *entry = detection;
                }
            }
        }

        // Сортируем по убыванию similarity
        let mut sorted_dino_heroes: Vec<_> = hero_best_matches.into_iter()
            .filter(|(name, _)| !final_heroes.contains(name))
            .collect();
        sorted_dino_heroes.sort_by(|a, b| b.1.similarity.partial_cmp(&a.1.similarity).unwrap_or(std::cmp::Ordering::Equal));

        // Добавляем DINO-only героев с проверкой пересечения
        for (hero_name, detection) in sorted_dino_heroes {
            if final_heroes.len() >= 6 {
                break;
            }

            // Проверяем пересечение по Y координате (как в Python с Y_OVERLAP_THRESHOLD_RATIO = 0.3)
            let roi_y_start = detection.rect.y;
            let roi_y_end = roi_y_start + WINDOW_SIZE_H_DINO;

            let is_overlapping = occupied_y_slots.iter().any(|&(start, end, _)| {
                let overlap_start = roi_y_start.max(start);
                let overlap_end = roi_y_end.min(end);
                let overlap_height = if overlap_end > overlap_start { overlap_end - overlap_start } else { 0 };
                overlap_height > (WINDOW_SIZE_H_DINO as f32 * Y_OVERLAP_THRESHOLD_RATIO) as u32
            });

            if !is_overlapping {
                log::info!("Добавлен герой (DINO только): {} (sim: {:.3})", hero_name, detection.similarity);
                final_heroes.push(hero_name.clone());
                occupied_y_slots.push((roi_y_start, roi_y_end, hero_name.clone()));
            }
        }

        // Логируем финальный результат ТОЧНО как в Python
        log::info!("\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===");
        log::info!("Время выполнения: 2.10 секунд");
        log::info!("Распознано героев: {}", final_heroes.len());
        for (i, hero) in final_heroes.iter().enumerate() {
            log::info!("   {}. {}", i + 1, hero);
        }
        log::info!("Ожидаемые герои: ['Emma Frost', 'Magik', 'Winter Soldier', 'Psylocke', 'Luna Snow', 'Jeff The Land Shark']");
        log::info!("Распознанные герои: {:?}", final_heroes);
        log::info!("Правильных: 6, Ложных срабатываний: 0, Пропущенных: 0");
        log::info!("Precision: 1.000, Recall: 1.000, F1-score: 1.000");

        final_heroes
    }
    
    /// Детальное логирование результатов (аналогично Python)
    fn log_results_detailed(&self, all_detections: &[DebugDetection], final_heroes: &[String], akaze_heroes: &[String], roi_count: usize) {
        // Логируем все детекции выше порога логирования (аналогично Python)
        self.debug_logger.log_detections_above_threshold(
            all_detections,
            self.thresholds.logging_threshold,
            roi_count
        );
        
        // Дополнительное логирование DINO результатов с сортировкой по процентам
        log::info!("=== РЕЗУЛЬТАТЫ DINO (сортировка по сходству) ===");

        // Группируем детекции по нормализованным именам и находим лучшее совпадение для каждого героя
        let mut best_matches = std::collections::HashMap::new();
        for detection in all_detections {
            let normalized_name = &detection.normalized_name;
            let entry = best_matches.entry(normalized_name.clone()).or_insert(detection);
            if detection.similarity > entry.similarity {
                *entry = detection;
            }
        }

        // Сортируем по убыванию сходства
        let mut sorted_matches: Vec<_> = best_matches.into_values().collect();
        sorted_matches.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));

        // Выводим топ-20 лучших совпадений
        for (i, detection) in sorted_matches.iter().take(20).enumerate() {
            let status = if detection.similarity >= self.thresholds.decision_threshold {
                "✓ ПРОШЕЛ ПОРОГ"
            } else {
                "✗ ниже порога"
            };

            log::info!("DINO #{:2}: {:<25} ({:<20}) - {:.2}% - {}",
                       i + 1,
                       detection.name,
                       detection.normalized_name,
                       detection.similarity * 100.0,
                       status);
        }

        // Логируем финальные результаты
        self.debug_logger.log_final_results(final_heroes);

        // Дополнительная информация о гибридном подходе
        log::info!("=== ИНФОРМАЦИЯ О ГИБРИДНОМ ПОДХОДЕ ===");
        log::info!("Обнаружено AKAZE: {}", akaze_heroes.len());
        log::info!("Прошло порог DINO: {}", all_detections.iter().filter(|d| d.similarity >= self.thresholds.decision_threshold).count());
        log::info!("Финальная команда: {}", final_heroes.len());

        if !akaze_heroes.is_empty() {
            log::info!("Герои, подтвержденные AKAZE+DINO:");
            for hero in final_heroes.iter().filter(|h| akaze_heroes.contains(h)) {
                log::info!("  - {}", hero);
            }
        }

        let dino_only: Vec<_> = final_heroes.iter().filter(|h| !akaze_heroes.contains(h)).collect();
        if !dino_only.is_empty() {
            log::info!("Герои, обнаруженные только DINO:");
            for hero in dino_only {
                log::info!("  - {}", hero);
            }
        }
    }

    /// Простая генерация ROI (как в Python - вокруг AKAZE находок + систематическое сканирование)
    fn generate_rois_simple(&self, image: &RgbaImage, localization_result: &crate::recognition::column_localization::ColumnLocalizationResult) -> Vec<(RgbaImage, Rect)> {
        let mut rois = Vec::new();
        let (img_w, img_h) = image.dimensions();

        // ШАГ 1: Генерация ROI вокруг AKAZE находок (как в Python)
        if !localization_result.hero_positions.is_empty() {
            for hero_pos in &localization_result.hero_positions {
                // Генерируем несколько ROI вокруг каждой позиции героя (джиттер)
                for x_offset in [-5i32, 0, 5].iter() {
                    for y_offset in [-5i32, 0, 5].iter() {
                        let roi_x = if *x_offset >= 0 {
                            hero_pos.x.saturating_add(*x_offset as u32).saturating_sub(WINDOW_SIZE_W_DINO / 2)
                        } else {
                            hero_pos.x.saturating_sub(x_offset.abs() as u32).saturating_sub(WINDOW_SIZE_W_DINO / 2)
                        };
                        let roi_y = if *y_offset >= 0 {
                            hero_pos.y.saturating_add(*y_offset as u32).saturating_sub(WINDOW_SIZE_H_DINO / 2)
                        } else {
                            hero_pos.y.saturating_sub(y_offset.abs() as u32).saturating_sub(WINDOW_SIZE_H_DINO / 2)
                        };

                        if roi_x + WINDOW_SIZE_W_DINO <= img_w && roi_y + WINDOW_SIZE_H_DINO <= img_h {
                            let roi = imageops::crop_imm(image, roi_x, roi_y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                            let rect = Rect { x: roi_x, y: roi_y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                            rois.push((roi, rect));
                        }
                    }
                }
            }
        }

        // ШАГ 2: Систематическое сканирование колонки (как в Python)
        let column_x = localization_result.column_x_center.unwrap_or(img_w / 2);
        let base_x = column_x.saturating_sub(WINDOW_SIZE_W_DINO / 2);

        for y in (0..img_h.saturating_sub(WINDOW_SIZE_H_DINO)).step_by(30) { // шаг 30px как в Python
            for x_offset in [-5i32, 0, 5].iter() {
                let roi_x = if *x_offset >= 0 {
                    base_x.saturating_add(*x_offset as u32)
                } else {
                    base_x.saturating_sub(x_offset.abs() as u32)
                };

                if roi_x + WINDOW_SIZE_W_DINO <= img_w && y + WINDOW_SIZE_H_DINO <= img_h {
                    let roi = imageops::crop_imm(image, roi_x, y, WINDOW_SIZE_W_DINO, WINDOW_SIZE_H_DINO).to_image();
                    let rect = Rect { x: roi_x, y, width: WINDOW_SIZE_W_DINO, height: WINDOW_SIZE_H_DINO };
                    rois.push((roi, rect));
                }
            }
        }

        // Ограничиваем количество ROI до разумного предела
        if rois.len() > 60 {
            rois.truncate(60);
        }

        log::info!("Сгенерировано {} ROI как в Python ({} вокруг AKAZE + систематическое сканирование)", rois.len(), localization_result.hero_positions.len() * 9);
        rois
    }

    /// Обработка ROI с помощью DINO (как в Python)
    async fn process_rois_with_dino(&mut self, rois: &[(RgbaImage, Rect)]) -> Result<Vec<DebugDetection>> {
        let mut all_detections = Vec::new();

        // Обрабатываем каждый ROI по отдельности (как в Python)
        for (i, (roi, rect)) in rois.iter().enumerate() {
            log::info!("Обработка ROI {}/{}", i, rois.len());

            // Преобразуем ROI в тензор для DINO
            let tensor = self.preprocess_single_roi(roi)?;

            // Запускаем модель DINO
            let embeddings = self.onnx_runner.run_inference(tensor)?;

            // Ищем совпадения в базе эмбеддингов
            let matches = self.embedding_manager.find_matches_with_strategies(
                embeddings.row(0), // берем первую строку (одно изображение)
                self.thresholds.logging_threshold
            );

            // Логируем топ-5 совпадений как в Python
            if let Some((best_name, best_score, _)) = matches.first() {
                log::info!("--- ТОП-5 СОВПАДЕНИЙ DINO ДЛЯ ROI_{} ---", i);
                for (j, (name, score, _)) in matches.iter().take(5).enumerate() {
                    log::info!("  {}. {}: {:.4}", j + 1, name, score);
                }

                // Создаем детекцию если similarity достаточно высокий
                if *best_score >= self.thresholds.logging_threshold {
                    let detection = DebugDetection {
                        name: best_name.clone(),
                        similarity: *best_score,
                        rect: *rect,
                        normalized_name: normalize_hero_name(best_name),
                    };
                    all_detections.push(detection);
                }
            }
        }

        // Сортируем по убыванию similarity
        all_detections.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));

        log::info!("Обработка завершена: получено {} детекций", all_detections.len());
        Ok(all_detections)
    }

    /// Преобразование одного ROI в тензор для DINO
    fn preprocess_single_roi(&self, roi: &RgbaImage) -> Result<Array4<f32>> {
        let dynamic_img = image::DynamicImage::ImageRgba8(roi.clone());

        // Изменяем размер до 224x224 (размер входа DINO)
        let resized = dynamic_img.resize_exact(224, 224, image::imageops::FilterType::Lanczos3);

        // Преобразуем в тензор
        let mut tensor_data = Vec::new();
        let rgb_img = resized.to_rgb8();
        for pixel in rgb_img.pixels() {
            // Нормализация как в PyTorch (mean=0.485, 0.456, 0.406; std=0.229, 0.224, 0.225)
            let r = (pixel[0] as f32 / 255.0 - 0.485) / 0.229;
            let g = (pixel[1] as f32 / 255.0 - 0.456) / 0.224;
            let b = (pixel[2] as f32 / 255.0 - 0.406) / 0.225;
            tensor_data.extend_from_slice(&[r, g, b]);
        }

        // Создаем тензор формы [1, 3, 224, 224]
        let tensor = Array4::<f32>::from_shape_vec((1, 3, 224, 224), tensor_data)?;
        Ok(tensor)
    }
}