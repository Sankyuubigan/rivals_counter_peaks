#!/usr/bin/env rust-script
//! ```cargo
//! [dependencies]
//! image = "0.24"
//! ort = { version = "2.0.0-rc.10", features = ["ndarray"] }
//! ndarray = { version = "0.15", features = ["serde"] }
//! ndarray-npy = "0.8"
//! log = "0.4"
//! simplelog = "0.12"
//! serde = { version = "1.0", features = ["derive"] }
//! serde_json = "1.0"
//! anyhow = "1.0"
//! num-traits = "0.2"
//! ```
use anyhow::{Context, Result};
use image::{DynamicImage, GenericImageView, ImageBuffer};
use log::{info, warn};
use ndarray::{s, Array1, Array2, Array4, Axis};
use ndarray_npy::read_npy;
use ort::session::builder::GraphOptimizationLevel;
use ort::session::Session;
use ort::value::Tensor;
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

// =============================================================================
// КОНСТАНТЫ
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
struct Detection {
    hero: String,
    confidence: f32,
    position: (u32, u32),
    size: (u32, u32),
}

struct HeroRecognitionSystem {
    session: Session,
    hero_embeddings: HashMap<String, Vec<Array1<f32>>>,
    debug_dir: PathBuf,
}

impl HeroRecognitionSystem {
    fn new(debug_dir: PathBuf) -> Result<Self> {
        info!("Инициализация системы распознавания героев...");
        let model_path = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx";
        let session = Session::builder()?
            .with_optimization_level(GraphOptimizationLevel::Level3)?
            .commit_from_file(model_path)
            .context("Не удалось загрузить модель ONNX")?;
        info!("Модель загружена. Вход: {}", session.inputs[0].name);
        let embeddings_dir = Path::new("resources/embeddings_padded");
        let mut hero_embeddings = HashMap::new();
        for entry in fs::read_dir(embeddings_dir)?.filter_map(Result::ok) {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("npy") {
                let file_stem = path.file_stem().unwrap().to_string_lossy();
                let parts: Vec<&str> = file_stem.split('_').collect();
                let hero_name = if parts.len() > 1 && parts.last().unwrap().parse::<u32>().is_ok() {
                    parts[..parts.len() - 1].join("_")
                } else {
                    file_stem.to_string()
                };
                let embedding: Array1<f32> = read_npy(&path)?;
                hero_embeddings
                    .entry(hero_name)
                    .or_insert_with(Vec::new)
                    .push(embedding);
            }
        }
        info!("Загружено эмбеддингов для {} героев", hero_embeddings.len());
        Ok(Self {
            session,
            hero_embeddings,
            debug_dir,
        })
    }

    fn crop_image_to_recognition_area(&self, image: &DynamicImage) -> DynamicImage {
        let (width, height) = image.dimensions();
        let area = (
            (width as f32 * 0.50) as u32,
            (height as f32 * 0.20) as u32,
            (width as f32 * 0.20) as u32,
            (height as f32 * 0.50) as u32,
        );
        image.crop_imm(area.0, area.1, area.2, area.3)
    }

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
        let mut background =
            ImageBuffer::from_pixel(target_size, target_size, image::Rgba([0, 0, 0, 255]));
        let paste_x = (target_size - new_w) / 2;
        let paste_y = (target_size - new_h) / 2;
        image::imageops::overlay(&mut background, &resized, paste_x.into(), paste_y.into());
        DynamicImage::ImageRgba8(background)
    }

    fn get_embeddings_for_batch(&mut self, images: &[DynamicImage]) -> Result<Array2<f32>> {
        let batch_size = images.len();
        let mut batch_array =
            Array4::zeros((batch_size, 3, TARGET_SIZE as usize, TARGET_SIZE as usize));
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
        let flat_data: Vec<f32> = batch_array.iter().cloned().collect();
        let dims: [usize; 4] = [
            batch_array.len_of(Axis(0)),
            batch_array.len_of(Axis(1)),
            batch_array.len_of(Axis(2)),
            batch_array.len_of(Axis(3)),
        ];
        let input_tensor = Tensor::from_array((dims.as_slice(), flat_data))?;
        let outputs = self.session.run(vec![("pixel_values", input_tensor)])?;
        let output_value = &outputs["last_hidden_state"];
        let output_tensor = output_value.try_extract_tensor::<f32>()?;
        let (ort_shape, data) = output_tensor;
        let seq_len = ort_shape[1] as usize;
        let emb_size = ort_shape[2] as usize;
        let batch_size = ort_shape[0] as usize;
        let mut embeddings = Vec::new();
        for i in 0..batch_size {
            let start = i * seq_len * emb_size;
            let end = start + emb_size;
            embeddings.extend_from_slice(&data[start..end]);
        }
        let embeddings_array = Array2::from_shape_vec((batch_size, emb_size), embeddings)?;
        let mut normalized_embeddings = Array2::zeros(embeddings_array.raw_dim());
        for (i, emb) in embeddings_array.axis_iter(Axis(0)).enumerate() {
            let norm = emb.mapv(|x| x.powi(2)).sum().sqrt();
            if norm > 1e-6 {
                normalized_embeddings
                    .slice_mut(s![i, ..])
                    .assign(&(&emb / norm));
            }
        }
        Ok(normalized_embeddings)
    }

    fn get_best_match(&self, query_embedding: &Array1<f32>) -> Option<(String, f32)> {
        self.hero_embeddings
            .iter()
            .flat_map(|(name, embeddings)| {
                embeddings
                    .iter()
                    .map(move |emb| (name.clone(), query_embedding.dot(emb)))
            })
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
    }

    fn method_fast_projection(&self, image: &DynamicImage) -> Vec<(u32, u32, u32, u32)> {
        let step_size = HERO_SQUARE_SIZE / 4;
        (0..=(image.height().saturating_sub(HERO_SQUARE_SIZE)))
            .step_by(step_size as usize)
            .map(|y| (LEFT_OFFSET, y, HERO_SQUARE_SIZE, HERO_SQUARE_SIZE))
            .collect()
    }

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

    pub fn recognize_heroes_optimized(&mut self, test_file_index: u32) -> Result<Vec<String>> {
        let scr_path = format!("tests/for_recogn/screenshots/{}.png", test_file_index);
        let img =
            image::open(&scr_path).context(format!("Не удалось открыть скриншот {}", scr_path))?;
        let cropped_img = self.crop_image_to_recognition_area(&img);

        let candidate_squares = self.method_fast_projection(&cropped_img);
        info!("Найдено {} кандидатов", candidate_squares.len());

        let rois_batch: Vec<_> = candidate_squares
            .iter()
            .map(|&(x, y, w, h)| cropped_img.crop_imm(x, y, w, h))
            .collect();

        let mut all_embeddings = Vec::new();
        for chunk in rois_batch.chunks(BATCH_SIZE) {
            let chunk_embeddings = self.get_embeddings_for_batch(chunk)?;
            for row in chunk_embeddings.axis_iter(Axis(0)) {
                all_embeddings.extend_from_slice(row.as_slice().unwrap());
            }
        }
        let all_embeddings =
            Array2::from_shape_vec((all_embeddings.len() / 768, 768), all_embeddings)?;

        let mut all_detections = Vec::new();
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
        info!(
            "Найдено {} детекций с уверенностью >= {:.2}",
            all_detections.len(),
            CONFIDENCE_THRESHOLD
        );

        // ПРИМЕНЯЕМ NMS ДЛЯ УДАЛЕНИЯ ПЕРЕСЕКАЮЩИХСЯ БОКСОВ
        self.apply_nms(&mut all_detections, 0.4);
        info!("Осталось {} детекций после NMS", all_detections.len());

        // Выбираем лучшего кандидата для каждого уникального героя
        let mut hero_dict = HashMap::new();
        for det in all_detections {
            hero_dict
                .entry(det.hero.clone())
                .and_modify(|e: &mut Detection| {
                    if det.confidence > e.confidence {
                        *e = det.clone();
                    }
                })
                .or_insert(det);
        }

        let mut final_detections: Vec<Detection> = hero_dict.into_values().collect();
        final_detections.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());
        final_detections.truncate(MAX_HEROES);
        final_detections.sort_by_key(|d| d.position.1);

        info!("\n=== РЕЗУЛЬТАТ РАСПОЗНАВАНИЯ ===");
        info!("Распознано героев: {}", final_detections.len());
        for (i, detection) in final_detections.iter().enumerate() {
            info!(
                "  {}. {} (уверенность: {:.3})",
                i + 1,
                normalize_hero_name_for_display(&detection.hero),
                detection.confidence
            );
        }

        Ok(final_detections.into_iter().map(|d| d.hero).collect())
    }
}

fn normalize_hero_name_for_display(hero_name: &str) -> String {
    let name_with_spaces = hero_name.replace('_', " ");
    let capitalized = name_with_spaces
        .split_whitespace()
        .map(|word| {
            let mut c = word.chars();
            match c.next() {
                None => String::new(),
                Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
            }
        })
        .collect::<Vec<String>>()
        .join(" ");
    capitalized.replace("And", "&")
}

#[derive(Debug, Deserialize)]
struct MetricsResult {
    correct: usize,
    false_positive: usize,
    false_negative: usize,
    precision: f32,
    recall: f32,
    f1: f32,
}

fn calculate_metrics(recognized: &[String], expected: &[String]) -> MetricsResult {
    let rec_set: HashSet<_> = recognized.iter().map(|s| s.as_str()).collect();
    let exp_set: HashSet<_> = expected.iter().map(|s| s.as_str()).collect();
    let correct = rec_set.intersection(&exp_set).count();
    let false_positive = rec_set.difference(&exp_set).count();
    let false_negative = exp_set.difference(&rec_set).count();
    let precision = if !rec_set.is_empty() {
        correct as f32 / rec_set.len() as f32
    } else {
        1.0
    };
    let recall = if !exp_set.is_empty() {
        correct as f32 / exp_set.len() as f32
    } else {
        1.0
    };
    let f1 = if precision + recall > 0.0 {
        2.0 * precision * recall / (precision + recall)
    } else {
        0.0
    };
    MetricsResult {
        correct,
        false_positive,
        false_negative,
        precision,
        recall,
        f1,
    }
}

fn main() -> Result<()> {
    let log_dir = PathBuf::from("tests/debug");
    if !log_dir.exists() {
        fs::create_dir_all(&log_dir)?;
    }
    let log_file = log_dir.join("recognition_test_rust.log");
    if log_file.exists() {
        fs::remove_file(&log_file)?;
    }

    use simplelog::*;
    CombinedLogger::init(vec![
        TermLogger::new(
            LevelFilter::Info,
            Config::default(),
            TerminalMode::Mixed,
            ColorChoice::Auto,
        ),
        WriteLogger::new(
            LevelFilter::Info,
            Config::default(),
            fs::File::create(&log_file)?,
        ),
    ])?;

    let mut system = HeroRecognitionSystem::new(PathBuf::from("tests/debug_rust"))?;
    info!("Система готова! Начинаем тестирование...");
    let answers_content = fs::read_to_string("tests/for_recogn/correct_answers.json")?;
    let correct_answers: HashMap<String, Vec<String>> = serde_json::from_str(&answers_content)?;
    let mut all_metrics = Vec::new();
    let mut recognition_times = Vec::new();

    for i in 1..=7 {
        if !Path::new(&format!("tests/for_recogn/screenshots/{}.png", i)).exists() {
            warn!("Скриншот {}.png не найден, пропуск.", i);
            continue;
        }
        info!(
            "\n{}\nТЕСТИРОВАНИЕ СКРИНШОТА {}\n{}",
            "=".repeat(80),
            i,
            "=".repeat(80)
        );
        let start_time = Instant::now();
        let recognized_raw = system.recognize_heroes_optimized(i)?;
        let duration = start_time.elapsed();
        recognition_times.push(duration);
        info!("Время выполнения: {:.3} секунд", duration.as_secs_f32());
        let expected = correct_answers
            .get(&i.to_string())
            .cloned()
            .unwrap_or_default();
        let recognized_norm: Vec<String> = recognized_raw
            .iter()
            .map(|h| normalize_hero_name_for_display(h))
            .collect();
        let metrics = calculate_metrics(&recognized_norm, &expected);
        info!("\n=== СРАВНЕНИЕ С ОЖИДАЕМЫМ РЕЗУЛЬТАТОМ ===");
        info!("Ожидаемые герои: {:?}", expected);
        info!("Распознанные герои: {:?}", recognized_norm);
        info!(
            "Правильных: {}, Ложных срабатываний: {}, Пропущенных: {}",
            metrics.correct, metrics.false_positive, metrics.false_negative
        );
        info!(
            "Precision: {:.3}, Recall: {:.3}, F1-score: {:.3}",
            metrics.precision, metrics.recall, metrics.f1
        );
        all_metrics.push((format!("Тест {}", i), metrics));
    }

    if !all_metrics.is_empty() {
        let total_tests = all_metrics.len();
        let avg_precision: f32 =
            all_metrics.iter().map(|(_, m)| m.precision).sum::<f32>() / total_tests as f32;
        let avg_recall: f32 =
            all_metrics.iter().map(|(_, m)| m.recall).sum::<f32>() / total_tests as f32;
        let avg_f1: f32 = all_metrics.iter().map(|(_, m)| m.f1).sum::<f32>() / total_tests as f32;
        info!(
            "\n{}\nСВОДНЫЙ ОТЧЕТ ПО ТЕСТИРОВАНИЮ\n{}",
            "=".repeat(60),
            "=".repeat(60)
        );
        info!("Всего тестов: {}", total_tests);
        info!("Средняя точность (Precision): {:.3}", avg_precision);
        info!("Средняя полнота (Recall): {:.3}", avg_recall);
        info!("Средний F1-score: {:.3}", avg_f1);
        info!("\nДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:\n{}", "-".repeat(80));
        info!(
            "{:<10} {:<8} {:<8} {:<8} {:<10} {:<10} {:<10}",
            "Тест", "Верных", "Ложных", "Пропущ", "Precision", "Recall", "F1"
        );
        info!("{}", "-".repeat(80));
        for (test_id, metrics) in &all_metrics {
            info!(
                "{:<10} {:<8} {:<8} {:<8} {:<10.3} {:<10.3} {:<10.3}",
                test_id,
                metrics.correct,
                metrics.false_positive,
                metrics.false_negative,
                metrics.precision,
                metrics.recall,
                metrics.f1
            );
        }
        info!("{}", "-".repeat(80));
    }

    if !recognition_times.is_empty() {
        let total_duration: Duration = recognition_times.iter().sum();
        let avg_time = total_duration / recognition_times.len() as u32;
        info!(
            "\nСреднее время распознавания одного скриншота: {:.3} секунд",
            avg_time.as_secs_f32()
        );
        info!("{}", "=".repeat(60));
    }

    Ok(())
}
