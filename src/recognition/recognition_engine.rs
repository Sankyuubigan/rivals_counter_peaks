use anyhow::Result;
use image::{imageops, RgbaImage};
use std::time::Instant;
use crate::utils::Rect;
use crate::recognition::embedding_manager::EmbeddingManager;
use crate::recognition::onnx_runner::OnnxRunner;
use crate::recognition::debug_logger::{DebugLogger, DebugDetection, DebugThresholds, normalize_hero_name, create_debug_session};
use crate::recognition::column_localization::localize_hero_column;
use crate::recognition::performance_optimizer::PerformanceOptimizer;
use ndarray::Array4;
use std::sync::{Arc, Mutex};
/// Параметры распознавания (аналог констант из Python)
const WINDOW_SIZE_W_DINO: u32 = 93;
const WINDOW_SIZE_H_DINO: u32 = 93;
const ROI_GENERATION_STRIDE_Y_DINO: u32 = (WINDOW_SIZE_H_DINO as f32 * 0.8) as u32;
const BATCH_SIZE_SLIDING_WINDOW_DINO: usize = 32;
// Снижаем пороги для улучшения распознавания
const DINOV2_LOGGING_SIMILARITY_THRESHOLD: f32 = 0.05; // Снижено с 0.10 до 0.05 (5%)
const DINOV2_FINAL_DECISION_THRESHOLD: f32 = 0.35; // Снижено с 0.65 до 0.35 (35%)
const DINO_CONFIRMATION_THRESHOLD_FOR_AKAZE: f32 = 0.25; // Снижено с 0.40 до 0.25 (25%)
const Y_OVERLAP_THRESHOLD_RATIO: f32 = 0.5;
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
    
    /// Основной метод распознавания героев на скриншоте
    pub async fn recognize_heroes(&mut self, screenshot: &RgbaImage) -> Result<Vec<String>> {
        let start_time = Instant::now();
        log::info!("--->>> recognize_heroes ВЫЗВАН <<<---");
        
        // Шаг 1: Локализация колонки с героями
        let dynamic_screenshot = image::DynamicImage::ImageRgba8(screenshot.clone());
        let localization_result = localize_hero_column(&dynamic_screenshot)?;
        
        log::info!("Результаты локализации колонки: центр X = {:?}, обнаружено героев: {}", 
                  localization_result.column_x_center, localization_result.detected_heroes.len());
        
        // Логируем результаты AKAZE (аналогично Python)
        if !localization_result.detected_heroes.is_empty() {
            log::info!("=== РЕЗУЛЬТАТЫ AKAZE ===");
            for (i, hero) in localization_result.detected_heroes.iter().enumerate() {
                log::info!("AKAZE {}: {}", i + 1, hero);
            }
        } else {
            log::warn!("AKAZE не обнаружил героев");
        }
        
        // Шаг 2: Генерация областей интереса (ROIs)
        let rois = self.generate_rois(screenshot, &localization_result);
        if rois.is_empty() {
            log::warn!("Не найдено областей интереса (ROIs) для обработки");
            return Ok(Vec::new());
        }
        
        log::info!("Сгенерировано {} ROIs для DINO", rois.len());
        
        // Шаг 3: Обработка ROIs пакетами с использованием оптимизатора производительности
        let all_detections = self.process_rois_optimized(&rois).await?;
        
        // Шаг 4: Фильтрация и постобработка результатов
        let final_heroes = self.filter_and_postprocess(&all_detections, &localization_result.detected_heroes);
        
        // Шаг 5: Логирование результатов
        self.log_results_detailed(&all_detections, &final_heroes, &localization_result.detected_heroes, rois.len());
        
        // Шаг 6: Сохранение отладочной информации
        if self.debug_logger.is_enabled() {
            let debug_session = create_debug_session(
                rois.len(),
                &all_detections,
                &final_heroes,
                self.thresholds.clone(),
            );
            if let Err(e) = self.debug_logger.save_session(&debug_session) {
                log::error!("Ошибка сохранения отладочной сессии: {}", e);
            }
        }
        
        let duration = start_time.elapsed();
        log::info!("<<<--- recognize_heroes ЗАВЕРШЕН за {:?} ---<<<", duration);
        
        Ok(final_heroes)
    }
    
    /// Генерирует области интереса (ROIs) для сканирования
    fn generate_rois(&self, image: &RgbaImage, localization_result: &crate::recognition::column_localization::ColumnLocalizationResult) -> Vec<(RgbaImage, Rect)> {
        let mut rois = Vec::new();
        let (img_w, img_h) = image.dimensions();
        
        log::debug!("Генерация ROIs для изображения размером {}x{}", img_w, img_h);
        
        // Ограничиваем максимальное количество ROI
        const MAX_ROIS: usize = 150;
        let mut generated_count = 0;
        
        // Если удалось определить центр колонки, генерируем ROI вокруг него
        if let Some(column_x_center) = localization_result.column_x_center {
            let base_roi_start_x = column_x_center.saturating_sub(WINDOW_SIZE_W_DINO / 2);
            
            log::info!("Генерация ROI для DINO. Базовый левый край ROI X={} (на основе центра X={}). Шаг Y={}",
                       base_roi_start_x, column_x_center, ROI_GENERATION_STRIDE_Y_DINO);
            
            for y in (0..img_h).step_by(ROI_GENERATION_STRIDE_Y_DINO as usize) {
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
        } else {
            // Если не удалось определить центр колонки, используем fallback-режим (полное сканирование)
            log::warn!("Не удалось определить X-координату центра колонки. Включается fallback DINO (полное сканирование).");
            
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
    
    /// Фильтрует детекции и применяет постобработку
    fn filter_and_postprocess(&self, detections: &[DebugDetection], akaze_detected_heroes: &[String]) -> Vec<String> {
        let mut final_heroes = Vec::new();
        let mut occupied_y_slots = Vec::new();
        
        // Фильтруем детекции выше порога принятия решения
        let high_confidence_detections: Vec<_> = detections
            .iter()
            .filter(|d| d.similarity >= self.thresholds.decision_threshold)
            .collect();
        
        log::info!("Детекций выше порога решения ({:.1}%): {}", 
                   self.thresholds.decision_threshold * 100.0, 
                   high_confidence_detections.len());
        
        // Гибридный подход: сначала добавляем героев, обнаруженных AKAZE
        for akaze_hero in akaze_detected_heroes {
            if final_heroes.len() >= 6 { // Максимальный размер команды
                break;
            }
            
            // Проверяем, не добавлен ли уже этот герой
            if final_heroes.contains(akaze_hero) {
                continue;
            }
            
            // Ищем лучшее совпадение DINO для этого героя
            if let Some(best_dino_match) = detections.iter()
                .filter(|d| normalize_hero_name(&d.name) == *akaze_hero && d.similarity >= self.thresholds.confirmation_threshold)
                .max_by(|a, b| a.similarity.partial_cmp(&b.similarity).unwrap_or(std::cmp::Ordering::Equal)) {
                
                // Проверяем пересечение по Y координате
                let roi_y_start = best_dino_match.rect.y;
                let roi_y_end = roi_y_start + WINDOW_SIZE_H_DINO;
                
                let is_overlapping = occupied_y_slots.iter().any(|&(start, end, _)| {
                    let overlap_start = roi_y_start.max(start);
                    let overlap_end = roi_y_end.min(end);
                    let overlap_height = overlap_end.saturating_sub(overlap_start);
                    overlap_height > (WINDOW_SIZE_H_DINO as f32 * Y_OVERLAP_THRESHOLD_RATIO) as u32
                });
                
                if !is_overlapping {
                    final_heroes.push(akaze_hero.clone());
                    occupied_y_slots.push((roi_y_start, roi_y_end, akaze_hero.clone()));
                    
                    log::info!("Добавлен '{}' (AKAZE+DINO) с DINO sim: {:.1}%. Занятый Y-слот: ({})",
                               best_dino_match.name, best_dino_match.similarity * 100.0, roi_y_start);
                } else {
                    log::debug!("Кандидат '{}' (AKAZE+DINO) пересекается с уже добавленным, пропуск",
                                best_dino_match.name);
                }
            } else {
                log::warn!("AKAZE нашел '{}', но DINO не подтвердил его с достаточной уверенностью (>{:.1}%)",
                           akaze_hero, self.thresholds.confirmation_threshold * 100.0);
            }
        }
        
        // Затем добавляем оставшихся героев, обнаруженных только DINO
        for detection in high_confidence_detections {
            if final_heroes.len() >= 6 { // Максимальный размер команды
                break;
            }
            
            let normalized_name = &detection.normalized_name;
            
            // Проверяем, не добавлен ли уже этот герой
            if final_heroes.contains(normalized_name) {
                continue;
            }
            
            // Проверяем пересечение по Y координате
            let roi_y_start = detection.rect.y;
            let roi_y_end = roi_y_start + WINDOW_SIZE_H_DINO;
            
            let is_overlapping = occupied_y_slots.iter().any(|&(start, end, _)| {
                let overlap_start = roi_y_start.max(start);
                let overlap_end = roi_y_end.min(end);
                let overlap_height = overlap_end.saturating_sub(overlap_start);
                overlap_height > (WINDOW_SIZE_H_DINO as f32 * Y_OVERLAP_THRESHOLD_RATIO) as u32
            });
            
            if !is_overlapping {
                final_heroes.push(normalized_name.clone());
                occupied_y_slots.push((roi_y_start, roi_y_end, normalized_name.clone()));
                
                log::info!("Добавлен '{}' (только DINO) с DINO sim: {:.1}%. Занятый Y-слот: ({})",
                           detection.name, detection.similarity * 100.0, roi_y_start);
            } else {
                log::debug!("Кандидат '{}' (только DINO) пересекается с уже добавленным, пропуск",
                            detection.name);
            }
        }
        
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
}