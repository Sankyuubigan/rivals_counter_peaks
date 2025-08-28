use anyhow::Result;
use image::{DynamicImage, GenericImageView, ImageBuffer, RgbaImage};
use ndarray::{Array1, Array2, Array4, Axis};
use std::collections::HashMap;
use std::time::Instant;
use crate::recognition::embedding_manager::EmbeddingManager;
use crate::recognition::onnx_runner::OnnxRunner;

// =============================================================================
// КОНСТАНТЫ (как в эталонном алгоритме)
// =============================================================================
const TARGET_SIZE: u32 = 224;
const LEFT_OFFSET: u32 = 45;
const IMAGE_MEAN: [f32; 3] = [0.485, 0.456, 0.406];
const IMAGE_STD: [f32; 3] = [0.229, 0.224, 0.225];
const CONFIDENCE_THRESHOLD: f32 = 0.70;
const MAX_HEROES: usize = 6;
const HERO_SQUARE_SIZE: u32 = 95;
const BATCH_SIZE: usize = 32;

#[derive(Debug, Clone, PartialEq)]
pub struct Detection {
    pub hero: String,
    pub confidence: f32,
    pub position: (u32, u32),
    pub size: (u32, u32),
}

/// Простой движок распознавания героев на основе эталонного алгоритма
pub struct SimpleRecognitionEngine {
    onnx_runner: OnnxRunner,
    embedding_manager: EmbeddingManager,
}

impl SimpleRecognitionEngine {
    /// Создает новый экземпляр SimpleRecognitionEngine
    pub fn new() -> Result<Self> {
        log::info!("Инициализация простого движка распознавания героев...");

        let embedding_manager = EmbeddingManager::new()?;
        let onnx_runner = OnnxRunner::new()?;

        log::info!("Простой движок распознавания успешно инициализирован");
        Ok(Self {
            onnx_runner,
            embedding_manager,
        })
    }

    /// Основной метод распознавания героев (адаптация эталонного алгоритма)
    pub async fn recognize_heroes(&mut self, screenshot: &RgbaImage) -> Result<Vec<String>> {
        let start_time = Instant::now();
        log::info!("--->>> simple_recognize_heroes ВЫЗВАН <<<---");

        // Шаг 1: Обрезка области распознавания
        let dynamic_img = DynamicImage::ImageRgba8(screenshot.clone());
        let cropped_img = self.crop_image_to_recognition_area(&dynamic_img);

        // Шаг 2: Генерация кандидатов (быстрая проекция)
        let candidate_squares = self.method_fast_projection(&cropped_img);
        log::info!("Найдено {} кандидатов", candidate_squares.len());

        // Шаг 3: Получение эмбеддингов для всех кандидатов батчами
        let mut all_embeddings = Vec::new();
        let candidate_images: Vec<DynamicImage> = candidate_squares
            .iter()
            .map(|&(x, y, w, h)| cropped_img.crop_imm(x, y, w, h))
            .collect();

        for chunk in candidate_images.chunks(BATCH_SIZE) {
            let chunk_embeddings = self.get_embeddings_for_batch(chunk).await?;
            for row in chunk_embeddings.axis_iter(Axis(0)) {
                all_embeddings.extend_from_slice(row.as_slice().unwrap());
            }
        }

        let all_embeddings = Array2::from_shape_vec(
            (all_embeddings.len() / 768, 768),
            all_embeddings
        )?;

        // Шаг 4: Поиск лучших совпадений
        let mut all_detections = Vec::new();
        let num_embeddings = all_embeddings.shape()[0];
        let num_candidates = candidate_squares.len();

        if num_embeddings != num_candidates {
            log::warn!("Несоответствие количества эмбеддингов ({}) и кандидатов ({})", num_embeddings, num_candidates);
            // Обрежем до минимального количества
            let min_count = num_embeddings.min(num_candidates);
            for i in 0..min_count {
                let embedding = all_embeddings.row(i);
                if let Some((hero, confidence)) = self.get_best_match(&embedding.to_owned()) {
                    if confidence >= CONFIDENCE_THRESHOLD {
                        let (x, y, w, h) = candidate_squares[i];
                        all_detections.push(Detection {
                            hero,
                            confidence,
                            position: (x, y),
                            size: (w, h),
                        });
                    }
                }
            }
        } else {
            for (i, embedding) in all_embeddings.axis_iter(Axis(0)).enumerate() {
                if let Some((hero, confidence)) = self.get_best_match(&embedding.to_owned()) {
                    if confidence >= CONFIDENCE_THRESHOLD {
                        let (x, y, w, h) = candidate_squares[i];
                        all_detections.push(Detection {
                            hero,
                            confidence,
                            position: (x, y),
                            size: (w, h),
                        });
                    }
                }
            }
        }

        log::info!(
            "Найдено {} детекций с уверенностью >= {:.2}",
            all_detections.len(),
            CONFIDENCE_THRESHOLD
        );

        // Шаг 5: Применение NMS для удаления пересекающихся боксов
        self.apply_nms(&mut all_detections, 0.4);
        log::info!("Осталось {} детекций после NMS", all_detections.len());

        // Шаг 6: Выбор лучших кандидатов
        let final_detections = self.select_best_candidates(all_detections);

        // Шаг 7: Формирование финального списка героев с нормализацией имен
        let final_heroes: Vec<String> = final_detections
            .into_iter()
            .map(|d| crate::utils::normalize_hero_name(&d.hero))
            .collect();

        let duration = start_time.elapsed();
        log::info!("\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===");
        log::info!("Распознано героев: {}", final_heroes.len());
        for (i, hero) in final_heroes.iter().enumerate() {
            log::info!("  {}. {}", i + 1, hero);
        }
        log::info!("Имена героев успешно нормализованы для базы данных");
        log::info!("Время выполнения: {:.3} секунд", duration.as_secs_f32());

        log::info!("<<<--- simple_recognize_heroes ЗАВЕРШЕН за {:?} ---<<<", duration);
        Ok(final_heroes)
    }

    /// Обрезка изображения до области распознавания (как в эталонном алгоритме)
    fn crop_image_to_recognition_area(&self, image: &DynamicImage) -> DynamicImage {
        let (width, height) = image.dimensions();
        let area = (
            (width as f32 * 0.50) as u32,  // x
            (height as f32 * 0.20) as u32, // y
            (width as f32 * 0.20) as u32,  // width
            (height as f32 * 0.50) as u32, // height
        );
        image.crop_imm(area.0, area.1, area.2, area.3)
    }

    /// Дополнение изображения до целевого размера
    fn pad_image_to_target_size(&self, image: &DynamicImage, target_size: u32) -> DynamicImage {
        let (w, h) = image.dimensions();
        if w == target_size && h == target_size {
            return image.clone();
        }

        let aspect_ratio = w as f32 / h as f32;
        let (new_w, new_h) = if w > h {
            (target_size, (target_size as f32 / aspect_ratio) as u32)
        } else {
            ((target_size as f32 * aspect_ratio) as u32, target_size)
        };

        let resized = image.resize_exact(new_w, new_h, image::imageops::FilterType::Lanczos3);
        let mut background = ImageBuffer::from_pixel(target_size, target_size, image::Rgba([0, 0, 0, 255]));
        let paste_x = (target_size - new_w) / 2;
        let paste_y = (target_size - new_h) / 2;
        image::imageops::overlay(&mut background, &resized, paste_x.into(), paste_y.into());
        DynamicImage::ImageRgba8(background)
    }

    /// Получение эмбеддингов для батча изображений
    async fn get_embeddings_for_batch(&mut self, images: &[DynamicImage]) -> Result<Array2<f32>> {
        let batch_size = images.len();
        let mut batch_array = Array4::zeros((batch_size, 3, TARGET_SIZE as usize, TARGET_SIZE as usize));

        // Подготовка батча
        for (i, img) in images.iter().enumerate() {
            let padded = self.pad_image_to_target_size(img, TARGET_SIZE);
            let rgb_img = padded.to_rgb8();

            for y in 0..TARGET_SIZE {
                for x in 0..TARGET_SIZE {
                    let pixel = rgb_img.get_pixel(x, y);
                    batch_array[[i, 0, y as usize, x as usize]] =
                        (pixel[0] as f32 / 255.0 - IMAGE_MEAN[0]) / IMAGE_STD[0];
                    batch_array[[i, 1, y as usize, x as usize]] =
                        (pixel[1] as f32 / 255.0 - IMAGE_MEAN[1]) / IMAGE_STD[1];
                    batch_array[[i, 2, y as usize, x as usize]] =
                        (pixel[2] as f32 / 255.0 - IMAGE_MEAN[2]) / IMAGE_STD[2];
                }
            }
        }

        // Выполнение модели
        let outputs = self.onnx_runner.run_inference(batch_array)?;

        // Извлечение эмбеддингов (модель возвращает готовые эмбеддинги)
        log::debug!("Форма выхода модели: {:?}", outputs.shape());
        let embeddings_array = if outputs.shape().len() == 2 {
            // Модель возвращает готовые эмбеддинги формы [batch_size, embedding_size]
            outputs.to_owned()
        } else if outputs.shape().len() == 3 {
            // Модель возвращает последовательность токенов, берем CLS токен (первый токен)
            let seq_len = outputs.shape()[1];
            let emb_size = outputs.shape()[2];
            let batch_size_out = outputs.shape()[0];

            let mut embeddings = Vec::new();
            for i in 0..batch_size_out {
                let start = i * seq_len * emb_size;
                let end = start + emb_size;
                embeddings.extend_from_slice(&outputs.as_slice().unwrap()[start..end]);
            }
            Array2::from_shape_vec((batch_size_out, emb_size), embeddings)?
        } else {
            return Err(anyhow::anyhow!("Неверная форма выхода модели: ожидалось 2 или 3 измерения, получено {}", outputs.shape().len()));
        };

        // Нормализация эмбеддингов
        let mut normalized_embeddings = Array2::zeros(embeddings_array.raw_dim());
        for (i, emb) in embeddings_array.axis_iter(Axis(0)).enumerate() {
            let norm = emb.mapv(|x| x.powi(2)).sum().sqrt();
            if norm > 1e-6 {
                normalized_embeddings
                    .slice_mut(ndarray::s![i, ..])
                    .assign(&(&emb / norm));
            }
        }

        Ok(normalized_embeddings)
    }

    /// Поиск лучшего совпадения для эмбеддинга
    fn get_best_match(&self, query_embedding: &Array1<f32>) -> Option<(String, f32)> {
        self.embedding_manager
            .find_best_match(query_embedding.view(), CONFIDENCE_THRESHOLD)
    }

    /// Быстрая проекция для генерации кандидатов
    fn method_fast_projection(&self, image: &DynamicImage) -> Vec<(u32, u32, u32, u32)> {
        let step_size = HERO_SQUARE_SIZE / 4; // 23.75 пикселей
        (0..=(image.height().saturating_sub(HERO_SQUARE_SIZE)))
            .step_by(step_size as usize)
            .map(|y| (LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
            .collect()
    }

    /// Применение Non-Maximum Suppression
    fn apply_nms(&self, detections: &mut Vec<Detection>, iou_threshold: f32) {
        detections.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        let mut i = 0;
        while i < detections.len() {
            let mut j = i + 1;
            while j < detections.len() {
                let det_i = &detections[i];
                let det_j = &detections[j];

                let i_x1 = det_i.position.0 as i32;
                let i_y1 = det_i.position.1 as i32;
                let i_x2 = i_x1 + det_i.size.0 as i32;
                let i_y2 = i_y1 + det_i.size.1 as i32;

                let j_x1 = det_j.position.0 as i32;
                let j_y1 = det_j.position.1 as i32;
                let j_x2 = j_x1 + det_j.size.0 as i32;
                let j_y2 = j_y1 + det_j.size.1 as i32;

                let intersection_x1 = i_x1.max(j_x1);
                let intersection_y1 = i_y1.max(j_y1);
                let intersection_x2 = i_x2.min(j_x2);
                let intersection_y2 = i_y2.min(j_y2);

                let intersection_w = (intersection_x2 - intersection_x1).max(0);
                let intersection_h = (intersection_y2 - intersection_y1).max(0);
                let intersection_area = (intersection_w * intersection_h) as f32;

                let area_i = (det_i.size.0 * det_i.size.1) as f32;
                let area_j = (det_j.size.0 * det_j.size.1) as f32;
                let union_area = area_i + area_j - intersection_area;

                let iou = if union_area > 0.0 {
                    intersection_area / union_area
                } else {
                    0.0
                };

                if iou > iou_threshold {
                    detections.remove(j);
                } else {
                    j += 1;
                }
            }
            i += 1;
        }
    }

    /// Выбор лучших кандидатов (группировка по героям, выбор лучшего для каждого)
    fn select_best_candidates(&self, detections: Vec<Detection>) -> Vec<Detection> {
        // Группировка по героям
        let mut hero_groups: HashMap<String, Vec<Detection>> = HashMap::new();
        for detection in detections {
            hero_groups.entry(detection.hero.clone())
                      .or_insert_with(Vec::new)
                      .push(detection);
        }

        // Выбор лучшего кандидата для каждого героя
        let mut best_candidates: Vec<Detection> = hero_groups
            .into_iter()
            .map(|(_, mut detections)| {
                detections.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
                detections.into_iter().next().unwrap()
            })
            .collect();

        // Сортировка по уверенности и выбор топ MAX_HEROES
        best_candidates.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        best_candidates.truncate(MAX_HEROES);

        // Сортировка по позиции Y для корректного порядка
        best_candidates.sort_by_key(|d| d.position.1);

        best_candidates
    }
}