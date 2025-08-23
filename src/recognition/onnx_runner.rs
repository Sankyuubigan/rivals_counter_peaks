use anyhow::Result;
use ndarray::Array4;
use ort::session::{Session, builder::GraphOptimizationLevel};
use ort::value::Tensor;
use crate::utils::{get_absolute_path_string, file_exists};
// Используем модель dinov3-vitb16-pretrain-lvd1689m
const MODEL_PATH: &str = "vision_models/dinov3-vitb16-pretrain-lvd1689m/model_q4.onnx";
pub struct OnnxRunner {
    session: Session,
}
impl Clone for OnnxRunner {
    fn clone(&self) -> Self {
        // Создаем новый экземпляр с той же конфигурацией
        Self::new().unwrap_or_else(|_| {
            panic!("Не удалось клонировать OnnxRunner")
        })
    }
}
impl OnnxRunner {
    pub fn new() -> Result<Self> {
        log::debug!("Создание OnnxRunner");
        
        let absolute_model_path = get_absolute_path_string(MODEL_PATH);
        log::info!("Attempting to load model from: {}", absolute_model_path);
        
        // Проверяем существование файла модели
        if !file_exists(MODEL_PATH) {
            log::error!("ONNX model file not found at: {}", absolute_model_path);
            return Err(anyhow::anyhow!(
                "ONNX model file not found at: {}\nPlease check that the file exists in the specified directory.",
                absolute_model_path
            ));
        }
        
        // Создаем сессию с новым API
        log::debug!("Создание сессии ONNX");
        let session_result = Session::builder()?
            .with_optimization_level(GraphOptimizationLevel::Level1)?
            .commit_from_file(&absolute_model_path);
            
        if session_result.is_err() {
            let error_msg = format!("Failed to load ONNX model from '{}': {:?}", absolute_model_path, session_result.err().unwrap());
            log::error!("{}", error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }
        
        let session = session_result.unwrap();
            
        log::info!("ONNX model successfully loaded. Inputs: {}, Outputs: {}", session.inputs.len(), session.outputs.len());
        
        // Добавляем информацию о входах и выходах для отладки
        for (i, input) in session.inputs.iter().enumerate() {
            log::info!("Input {}: name='{}', type='{:?}'", i, input.name, input.input_type);
        }
        for (i, output) in session.outputs.iter().enumerate() {
            log::info!("Output {}: name='{}', type='{:?}'", i, output.name, output.output_type);
        }
        
        log::debug!("OnnxRunner успешно создан");
        Ok(Self { session })
    }
    
    pub fn run_inference(&mut self, tensor: Array4<f32>) -> Result<ndarray::Array2<f32>> {
        log::debug!("Начало выполнения нейронной сети");
        log::debug!("Форма входного тензора: {:?}", tensor.shape());
        
        // Создаем входные данные напрямую из формы и данных
        let shape = tensor.shape();
        let data = tensor.as_slice().unwrap();
        let input_tensor = Tensor::from_array((shape, data.to_vec()))?;
        
        // Создаем HashMap для входных данных с явным указанием типа
        let mut inputs: std::collections::HashMap<String, ort::value::Value> = std::collections::HashMap::new();
        // Используем правильное имя входа "pixel_values" вместо "input"
        inputs.insert("pixel_values".to_string(), input_tensor.into());
        
        // Сохраняем имя первого выхода до вызова метода run
        let output_name = self.session.outputs[0].name.clone();
        log::debug!("Используется выход: {}", output_name);
        
        log::debug!("Входной тензор подготовлен, выполнение модели...");
        let outputs_result = self.session.run(inputs);
        
        if outputs_result.is_err() {
            let error_msg = format!("Ошибка выполнения модели: {:?}", outputs_result.err().unwrap());
            log::error!("{}", error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }
        
        let outputs = outputs_result.unwrap();
        log::debug!("Модель выполнена успешно, количество выходов: {}", outputs.len());
        
        // Получаем первый выход по имени
        let output_tensor = outputs.get(&output_name)
            .ok_or_else(|| anyhow::anyhow!("Output '{}' not found in model outputs", output_name))?;
        
        // Извлекаем тензор с использованием try_extract_tensor
        let (shape, data) = output_tensor.try_extract_tensor::<f32>()?;
        log::debug!("Выходной тензор извлечен успешно с формой: {:?}", shape);
        
        // Преобразуем shape из &[i64] в Vec<usize> для создания ndarray
        let shape_vec: Vec<usize> = shape.iter().map(|&dim| dim as usize).collect();
        
        // Создаем ndarray из данных
        let output_array = ndarray::Array::from_shape_vec(
            ndarray::IxDyn(&shape_vec),
            data.to_vec()
        )?;
        
        // Преобразуем в ndarray Array3
        let output_array3_result = output_array.into_dimensionality::<ndarray::Ix3>();
        if output_array3_result.is_err() {
            let error_msg = format!("Ошибка преобразования в Array3: {:?}", output_array3_result.err().unwrap());
            log::error!("{}", error_msg);
            return Err(anyhow::anyhow!(error_msg));
        }
        
        let output_array3 = output_array3_result.unwrap();
        log::debug!("Форма выходного тензора: {:?}", output_array3.shape());
        
        // Извлекаем [CLS] токен для каждого элемента в пакете.
        // Он является первым токеном (индекс 0 по второй оси).
        let cls_embeddings = output_array3.slice(ndarray::s![.., 0, ..]).to_owned();
        log::debug!("CLS эмбеддинги извлечены с формой: {:?}", cls_embeddings.shape());
        
        log::debug!("Выполнение нейронной сети завершено успешно");
        Ok(cls_embeddings)
    }
}