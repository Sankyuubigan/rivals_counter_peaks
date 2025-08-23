use anyhow::Result;
use ndarray::Array4;
use ort::{
    session::Session,
    session::builder::GraphOptimizationLevel,
    value::Value
};
use crate::utils::{get_absolute_path_string, file_exists};

// Используем модель model_q4.onnx
const MODEL_PATH: &str = "vision_models/dinov2-base/model_q4.onnx";

pub struct OnnxRunnerSimple {
    session: Session,
}

impl OnnxRunnerSimple {
    pub fn new() -> Result<Self> {
        let absolute_model_path = get_absolute_path_string(MODEL_PATH);
        log::info!("Attempting to load model from: {}", absolute_model_path);
        
        // Проверяем существование файла модели перед попыткой загрузки
        if !file_exists(MODEL_PATH) {
            return Err(anyhow::anyhow!(
                "ONNX model file not found at: {}\nPlease check that the file exists in the specified directory.",
                absolute_model_path
            ));
        }
        
        // Создаем сессию без кастомных операций
        let session = ort::session::builder::SessionBuilder::new()?
            .with_optimization_level(GraphOptimizationLevel::Level1)?
            .commit_from_file(&absolute_model_path)?;
            
        log::info!("ONNX model successfully loaded. Inputs: {}, Outputs: {}", session.inputs.len(), session.outputs.len());
        Ok(Self { session })
    }
    
    /// Выполняет модель на пакете изображений.
    /// Возвращает пакет эмбеддингов [batch_size, embedding_dim].
    pub fn run_inference(&mut self, tensor: Array4<f32>) -> Result<ndarray::Array2<f32>> {
        log::info!("Running inference on tensor with shape: {:?}", tensor.shape());
        
        // Создаем входные данные
        let mut inputs = std::collections::HashMap::new();
        // Получаем форму и данные тензора
        let tensor_shape = tensor.shape().to_vec();
        let tensor_data = tensor.into_raw_vec();
        inputs.insert("pixel_values".to_string(), Value::from_array((tensor_shape, tensor_data))?);
        
        log::info!("Input tensor prepared, running model...");
        let outputs = self.session.run(inputs)?;
        
        log::info!("Model execution completed, processing outputs...");
        
        // Ожидаемый выход модели DINOv2 имеет форму [batch_size, num_tokens, embedding_dim]
        let output_tensor = outputs["output"].try_extract_tensor::<f32>()?;
        
        // Преобразуем shape из &[i64] в Vec<usize> для создания ndarray
        let shape_vec: Vec<usize> = output_tensor.0.iter().map(|&dim| dim as usize).collect();
        
        // Создаем ndarray из данных
        let output_array = ndarray::Array::from_shape_vec(
            ndarray::IxDyn(&shape_vec),
            output_tensor.1.to_vec()
        )?;
        let output_array3 = output_array.into_dimensionality::<ndarray::Ix3>()?;
        
        log::info!("Output tensor shape: {:?}", output_array3.shape());
        
        // Извлекаем [CLS] токен для каждого элемента в пакете.
        // Он является первым токеном (индекс 0 по второй оси).
        let cls_embeddings = output_array3.slice(ndarray::s![.., 0, ..]).to_owned();
        log::info!("CLS embeddings extracted with shape: {:?}", cls_embeddings.shape());
        
        Ok(cls_embeddings)
    }
}