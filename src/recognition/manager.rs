use anyhow::Result;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use crate::recognition::simple_recognition_engine::SimpleRecognitionEngine;
/// Состояние распознавания
#[derive(Debug, Clone, PartialEq)]
pub enum RecognitionState {
    Idle,
    Recognizing,
    Finished(Vec<String>), // Изменили с Result на Vec<String> для поддержки Clone
}
/// Менеджер распознавания героев
pub struct RecognitionManager {
    state: Arc<Mutex<RecognitionState>>,
    result_sender: mpsc::Sender<Result<Vec<String>>>,
    result_receiver: Option<mpsc::Receiver<Result<Vec<String>>>>,
    recognition_engine: Option<SimpleRecognitionEngine>,
    last_error: Option<String>, // Храним последнюю ошибку отдельно
}
impl RecognitionManager {
    /// Создает новый экземпляр RecognitionManager
    pub fn new() -> Result<Self> {
        let (result_sender, result_receiver) = mpsc::channel(1);
        
        Ok(Self {
            state: Arc::new(Mutex::new(RecognitionState::Idle)),
            result_sender,
            result_receiver: Some(result_receiver),
            recognition_engine: None,
            last_error: None,
        })
    }
    
    /// Запускает распознавание героев
    pub fn start_recognition(&mut self) {
        let current_state = self.get_state();
        if current_state == RecognitionState::Recognizing {
            log::warn!("Распознавание уже запущено");
            return;
        }
        
        log::info!("Запуск распознавания героев");
        *self.state.lock().unwrap() = RecognitionState::Recognizing;
        self.last_error = None;
        
        // Инициализируем движок распознавания при первом запуске
        if self.recognition_engine.is_none() {
            match SimpleRecognitionEngine::new() {
                Ok(engine) => {
                    self.recognition_engine = Some(engine);
                    log::info!("Движок распознавания успешно инициализирован");
                }
                Err(e) => {
                    let error_msg = format!("Ошибка инициализации движка распознавания: {}", e);
                    log::error!("{}", error_msg);
                    *self.state.lock().unwrap() = RecognitionState::Finished(Vec::new());
                    self.last_error = Some(error_msg);
                    return;
                }
            }
        }
        
        // Запускаем распознавание в отдельном потоке
        let state_clone = self.state.clone();
        let sender_clone = self.result_sender.clone();
        
        // Делаем скриншот в основном потоке, а обработку в фоновом
        let rgba_image_result = || -> Result<image::RgbaImage> {
            let monitors = xcap::Monitor::all()?;
            if let Some(monitor) = monitors.first() {
                let image = monitor.capture_image()?;
                let (width, height) = image.dimensions();
                let rgba_data = image.into_raw();
                let rgba_image = image::RgbaImage::from_raw(width, height, rgba_data)
                    .ok_or_else(|| anyhow::anyhow!("Не удалось создать RgbaImage из данных XCap"))?;
                Ok(rgba_image)
            } else {
                Err(anyhow::anyhow!("Не найдено доступных мониторов"))
            }
        }();
        
        match rgba_image_result {
            Ok(rgba_image) => {
                // Клонируем данные для передачи в поток
                let rgba_image_clone = rgba_image.clone();
                
                // Запускаем распознавание в отдельном потоке
                tokio::spawn(async move {
                    // Используем новый простой движок распознавания
                    let mut engine = match SimpleRecognitionEngine::new() {
                        Ok(engine) => engine,
                        Err(e) => {
                            let error_msg = format!("Ошибка создания движка распознавания: {}", e);
                            log::error!("{}", error_msg);
                            *state_clone.lock().unwrap() = RecognitionState::Finished(Vec::new());
                            let _ = sender_clone.send(Err(anyhow::anyhow!(error_msg))).await;
                            return;
                        }
                    };

                    match engine.recognize_heroes(&rgba_image_clone).await {
                        Ok(heroes) => {
                            log::info!("Распознавание завершено успешно: {:?}", heroes);
                            *state_clone.lock().unwrap() = RecognitionState::Finished(heroes.clone());
                            let _ = sender_clone.send(Ok(heroes)).await;
                        }
                        Err(e) => {
                            let error_msg = format!("Ошибка распознавания: {}", e);
                            log::error!("{}", error_msg);
                            *state_clone.lock().unwrap() = RecognitionState::Finished(Vec::new());
                            let _ = sender_clone.send(Err(anyhow::anyhow!(error_msg))).await;
                        }
                    }
                });
            }
            Err(e) => {
                let error_msg = format!("Не удалось сделать скриншот: {}", e);
                log::error!("{}", error_msg);
                *self.state.lock().unwrap() = RecognitionState::Finished(Vec::new());
                self.last_error = Some(error_msg);
            }
        }
    }
    
    /// Возвращает текущее состояние распознавания
    pub fn get_state(&self) -> RecognitionState {
        self.state.lock().unwrap().clone()
    }
    
    /// Возвращает последнюю ошибку, если она была
    pub fn get_last_error(&self) -> Option<&str> {
        self.last_error.as_deref()
    }
    
    /// Пытается получить результат распознавания, если он готов
    pub fn try_get_result(&mut self) -> Result<Option<Vec<String>>> {
        if let Some(ref mut receiver) = self.result_receiver {
            match receiver.try_recv() {
                Ok(result) => {
                    match result {
                        Ok(heroes) => Ok(Some(heroes)),
                        Err(e) => {
                            self.last_error = Some(format!("{}", e));
                            Ok(None)
                        }
                    }
                },
                Err(mpsc::error::TryRecvError::Empty) => Ok(None),
                Err(mpsc::error::TryRecvError::Disconnected) => {
                    Err(anyhow::anyhow!("Канал результатов отключен"))
                }
            }
        } else {
            Ok(None)
        }
    }
    
}