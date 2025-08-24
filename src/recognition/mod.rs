pub mod manager;
pub mod debug_logger;
pub mod embedding_manager;
pub mod image_enhancer;
pub mod image_preprocessing;
pub mod image_processor;
pub mod onnx_runner;
pub mod onnx_runner_simple;
pub mod post_processor;
pub mod recognition_engine;
pub mod column_localization;
pub mod performance_optimizer;
pub mod akaze_analysis;
pub mod akaze_opencv;
// Реэкспортируем основные типы
pub use manager::{RecognitionManager, RecognitionState};