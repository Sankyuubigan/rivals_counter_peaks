pub mod manager;
pub mod embedding_manager;
pub mod onnx_runner;
pub mod simple_recognition_engine;

// Реэкспортируем основные типы
pub use manager::{RecognitionManager, RecognitionState};