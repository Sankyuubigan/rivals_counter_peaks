use anyhow::Result;
use image::{RgbaImage, GenericImageView};
use ndarray::{Array4};
use crate::utils::Rect;
use std::sync::Arc;
use tokio::task::JoinSet;
use log::debug;
/// Оптимизатор производительности для распознавания героев
#[derive(Clone)]
pub struct PerformanceOptimizer {
    /// Максимальный размер пакета для параллельной обработки
    max_batch_size: usize,
    /// Максимальное количество параллельных задач
    max_parallel_tasks: usize,
}
impl Default for PerformanceOptimizer {
    fn default() -> Self {
        Self {
            max_batch_size: 64,  // Увеличиваем размер пакета
            max_parallel_tasks: 4,  // Количество параллельных задач
        }
    }
}
impl PerformanceOptimizer {
    pub fn new(max_batch_size: usize, max_parallel_tasks: usize) -> Self {
        Self {
            max_batch_size,
            max_parallel_tasks,
        }
    }
    
    /// Оптимизированная предобработка изображений с минимальным копированием данных
    pub fn preprocess_images_optimized(&self, rois: &[(RgbaImage, Rect)]) -> Result<Array4<f32>> {
        let start_time = std::time::Instant::now();
        
        // Предварительное выделение памяти для всего тензора
        let mut tensor = Array4::<f32>::zeros((rois.len(), 3, 224, 224));
        
        // Параметры нормализации для DINOv2
        let mean = [0.485, 0.456, 0.406];
        let std = [0.229, 0.224, 0.225];
        
        // Обработка каждого ROI
        for (i, (roi, _)) in rois.iter().enumerate() {
            // Конвертация в DynamicImage
            let dynamic_img = image::DynamicImage::ImageRgba8(roi.clone());
            
            // Изменение размера и обрезка
            let processed_img = self.crop_to_target_size_fast(dynamic_img, 224);
            let rgba_img = processed_img.to_rgba8();
            
            // Заполнение тензора напрямую без промежуточных выделений памяти
            for (x, y, pixel) in rgba_img.enumerate_pixels() {
                let [r, g, b, _] = pixel.0;
                tensor[[i, 0, y as usize, x as usize]] = (r as f32 / 255.0 - mean[0]) / std[0];
                tensor[[i, 1, y as usize, x as usize]] = (g as f32 / 255.0 - mean[1]) / std[1];
                tensor[[i, 2, y as usize, x as usize]] = (b as f32 / 255.0 - mean[2]) / std[2];
            }
        }
        
        debug!("Оптимизированная предобработка {} изображений завершена за {:?}", 
               rois.len(), start_time.elapsed());
        
        Ok(tensor)
    }
    
    /// Быстрая обрезка изображения до целевого размера
    fn crop_to_target_size_fast(&self, image: image::DynamicImage, target_size: u32) -> image::DynamicImage {
        let (width, height) = image.dimensions();
        
        // Вычисляем новые размеры с сохранением пропорций
        let (new_width, new_height) = if width < height {
            (target_size, (height * target_size / width))
        } else {
            ((width * target_size / height), target_size)
        };
        
        // Изменяем размер с использованием быстрого фильтра
        let img_resized = image.resize(new_width, new_height, image::imageops::FilterType::Nearest);
        
        // Центральная обрезка
        let left = (new_width - target_size) / 2;
        let top = (new_height - target_size) / 2;
        
        img_resized.crop_imm(left, top, target_size, target_size)
    }
    
    /// Параллельная обработка ROI с использованием tokio
    pub async fn process_rois_parallel<F, R>(
        &self,
        rois: Vec<(RgbaImage, Rect)>,
        process_func: Arc<F>,
    ) -> Vec<R>
    where
        F: Fn(Array4<f32>) -> R + Send + Sync + 'static,
        R: Send + 'static,
    {
        let start_time = std::time::Instant::now();
        
        // Создаем Arc для shared доступа к данным, чтобы решить проблему времени жизни
        let rois_arc = Arc::new(rois);
        
        // Разбиваем ROI на пакеты, используя Arc
        let batches: Vec<Vec<_>> = rois_arc
            .chunks(self.max_batch_size)
            .map(|chunk| chunk.to_vec())
            .collect();
        
        let batches_count = batches.len();
        
        debug!("Начало параллельной обработки {} пакетов (макс. {} задач параллельно)", 
               batches_count, self.max_parallel_tasks);
        
        let mut join_set = JoinSet::new();
        let mut results = Vec::new();
        
        // Обрабатываем пакеты параллельно
        for (batch_idx, batch) in batches.into_iter().enumerate() {
            // Создаем Arc для shared доступа к данным пакета
            let batch_arc = Arc::new(batch);
            let func_clone = Arc::clone(&process_func);
            
            // Ограничиваем количество параллельных задач
            if join_set.len() >= self.max_parallel_tasks {
                if let Some(result) = join_set.join_next().await {
                    match result {
                        Ok(batch_result) => results.push(batch_result),
                        Err(e) => {
                            debug!("Ошибка при обработке пакета: {:?}", e);
                            // Не добавляем ничего в результаты для этого пакета
                        }
                    }
                }
            }
            
            // Запускаем задачу в отдельном потоке
            let batch_clone = Arc::clone(&batch_arc);
            let func_clone_inner = Arc::clone(&func_clone);
            
            join_set.spawn(async move {
                debug!("Обработка пакета {}/{} ({} ROI)", 
                       batch_idx + 1, batches_count, batch_clone.len());
                
                let batch_start = std::time::Instant::now();
                
                // Предобработка изображений
                let tensor = crate::recognition::image_preprocessing::preprocess_image_batch(&batch_clone)
                    .unwrap_or_else(|e| {
                        debug!("Ошибка предобработки пакета {}: {:?}", batch_idx + 1, e);
                        Array4::zeros((0, 0, 0, 0))
                    });
                
                // Обработка с помощью переданной функции
                let result = func_clone_inner(tensor);
                
                debug!("Пакет {}/{} обработан за {:?}", 
                       batch_idx + 1, batches_count, batch_start.elapsed());
                
                result
            });
        }
        
        // Дожидаемся завершения оставшихся задач
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(batch_result) => results.push(batch_result),
                Err(e) => {
                    debug!("Ошибка при обработке пакета: {:?}", e);
                    // Не добавляем ничего в результаты для этого пакета
                }
            }
        }
        
        debug!("Параллельная обработка завершена за {:?}", start_time.elapsed());
        
        // Разворачиваем вектор результатов
        results.into_iter().collect()
    }
}