use crate::utils::{get_absolute_path_string, cosine_similarity};
use anyhow::{Context, Result};
use ndarray::{Array1, ArrayView1};
use std::collections::HashMap;
use std::fs;
const EMBEDDINGS_DIR: &str = "resources/embeddings_padded";
#[derive(Clone)]
pub struct EmbeddingManager {
    reference_embeddings: HashMap<String, Array1<f32>>,
    onnx_runner: Option<crate::recognition::onnx_runner::OnnxRunner>,
}
impl EmbeddingManager {
    pub fn new() -> Result<Self> {
        let absolute_embeddings_dir = get_absolute_path_string(EMBEDDINGS_DIR);
        log::info!("Загрузка эталонных эмбеддингов из директории: {}", absolute_embeddings_dir);
        let embeddings = load_reference_embeddings(&absolute_embeddings_dir)?;
        log::info!("Загружено {} эталонных эмбеддингов.", embeddings.len());
        Ok(Self { 
            reference_embeddings: embeddings,
            onnx_runner: None,
        })
    }
    
    pub fn set_onnx_runner(&mut self, runner: crate::recognition::onnx_runner::OnnxRunner) {
        self.onnx_runner = Some(runner);
    }
    
    pub fn get_onnx_runner(&self) -> &crate::recognition::onnx_runner::OnnxRunner {
        // В реальной реализации здесь должна быть обработка ошибки, если onnx_runner равен None
        self.onnx_runner.as_ref().unwrap()
    }
    
    pub fn find_best_match(
        &self,
        query_embedding: ArrayView1<f32>,
        threshold: f32,
    ) -> Option<(String, f32)> {
        let mut best_match: Option<(String, f32)> = None;
        let mut best_similarity = threshold;
        
        for (name, ref_emb) in &self.reference_embeddings {
            let similarity = cosine_similarity(query_embedding, ref_emb.view());
            
            if similarity > best_similarity {
                best_similarity = similarity;
                best_match = Some((name.clone(), similarity));
            }
        }
        
        best_match
    }
    
    // Новый метод для получения топ совпадений как в Python
    pub fn get_top_matches(
        &self,
        query_embedding: ArrayView1<f32>,
        threshold: f32,
        top_n: usize,
    ) -> Vec<(String, f32)> {
        let mut matches: Vec<(String, f32)> = Vec::new();
        
        for (name, ref_emb) in &self.reference_embeddings {
            let similarity = cosine_similarity(query_embedding, ref_emb.view());
            if similarity > threshold {
                matches.push((name.clone(), similarity));
            }
        }
        
        // Сортируем по убыванию сходства
        matches.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        // Возвращаем топ N совпадений
        matches.truncate(top_n);
        matches
    }
    
    // Метод для поиска совпадений с использованием нескольких стратегий
    pub fn find_matches_with_strategies(
        &self,
        query_embedding: ArrayView1<f32>,
        threshold: f32,
    ) -> Vec<(String, f32, String)> {
        let mut matches = Vec::new();
        
        for (name, ref_emb) in &self.reference_embeddings {
            // Косинусное сходство
            let cosine_sim = cosine_similarity(query_embedding, ref_emb.view());
            
            // Евклидово расстояние (нормализованное)
            let euclidean_dist = euclidean_distance_normalized(query_embedding, ref_emb.view());
            
            // Манхэттенское расстояние (нормализованное)
            let manhattan_dist = manhattan_distance_normalized(query_embedding, ref_emb.view());
            
            // Комбинированная метрика
            let combined_score = 0.6 * cosine_sim + 0.2 * (1.0 - euclidean_dist) + 0.2 * (1.0 - manhattan_dist);
            
            if combined_score > threshold {
                matches.push((name.clone(), combined_score, format!("cosine:{:.3},euclid:{:.3},manh:{:.3}", 
                                                              cosine_sim, euclidean_dist, manhattan_dist)));
            }
        }
        
        // Сортируем по убыванию комбинированной оценки
        matches.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        matches
    }
}
// Вычисление нормализованного евклидова расстояния
fn euclidean_distance_normalized(a: ArrayView1<f32>, b: ArrayView1<f32>) -> f32 {
    let mut sum = 0.0;
    for i in 0..a.len() {
        let diff = a[i] - b[i];
        sum += diff * diff;
    }
    let distance = sum.sqrt();
    // Нормализуем в диапазон [0, 1], где 0 означает полное совпадение
    1.0 / (1.0 + distance)
}
// Вычисление нормализованного манхэттенского расстояния
fn manhattan_distance_normalized(a: ArrayView1<f32>, b: ArrayView1<f32>) -> f32 {
    let mut sum = 0.0;
    for i in 0..a.len() {
        sum += (a[i] - b[i]).abs();
    }
    // Нормализуем в диапазон [0, 1], где 0 означает полное совпадение
    1.0 / (1.0 + sum)
}
fn load_reference_embeddings(dir_path: &str) -> Result<HashMap<String, Array1<f32>>> {
    let mut embeddings = HashMap::new();
    let entries = fs::read_dir(dir_path)
        .with_context(|| format!("Не удалось прочитать директорию с эмбеддингами: '{}'", dir_path))?;
    
    let mut file_count = 0;
    let mut success_count = 0;
    
    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) == Some("npy") {
            file_count += 1;
            if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                let data = std::fs::read(&path)
                    .with_context(|| format!("Не удалось прочитать файл эмбеддинга: {}", path.display()))?;
                
                let reader = npy::NpyData::from_bytes(&data)
                    .with_context(|| format!("Не удалось распарсить NPY файл: {}", path.display()))?;
                
                let data: Vec<f32> = reader.to_vec();
                let embedding = Array1::from(data);
                
                // Проверка на наличие NaN или Inf значений
                if embedding.iter().any(|x| x.is_nan() || x.is_infinite()) {
                    log::warn!("Эмбеддинг для '{}' содержит NaN или Inf значения и будет пропущен", stem);
                    continue;
                }
                
                embeddings.insert(stem.to_string(), embedding);
                success_count += 1;
            }
        }
    }
    
    log::info!("Найдено {} файлов .npy, успешно загружено {}", file_count, success_count);
    
    if embeddings.is_empty() {
        return Err(anyhow::anyhow!("В директории '{}' не найдено .npy файлов с эмбеддингами.", dir_path));
    }
    
    Ok(embeddings)
}