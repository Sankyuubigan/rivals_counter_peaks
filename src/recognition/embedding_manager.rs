use crate::utils::{get_absolute_path_string, cosine_similarity};
use anyhow::{Context, Result};
use ndarray::{Array1, ArrayView1};
use std::collections::HashMap;
use std::fs;
const EMBEDDINGS_DIR: &str = "resources/embeddings_padded";

#[derive(Clone)]
pub struct EmbeddingManager {
    reference_embeddings: HashMap<String, Array1<f32>>,
    // onnx_runner убран, так как он не использовался
}

impl EmbeddingManager {
    pub fn new() -> Result<Self> {
        let absolute_embeddings_dir = get_absolute_path_string(EMBEDDINGS_DIR);
        log::info!("Загрузка эталонных эмбеддингов из директории: {}", absolute_embeddings_dir);
        let embeddings = load_reference_embeddings(&absolute_embeddings_dir)?;
        log::info!("Загружено {} эталонных эмбеддингов.", embeddings.len());
        Ok(Self { 
            reference_embeddings: embeddings,
        })
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
    // Неиспользуемые методы удалены
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