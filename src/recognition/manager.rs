use anyhow::Result;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;
use crate::recognition::simple_recognition_engine::SimpleRecognitionEngine;
use image::RgbaImage;

/// Состояние распознавания
#[derive(Debug, Clone, PartialEq)]
pub enum RecognitionState {
    Idle,
    Recognizing,
    Finished(Vec<String>),
    Error(String),
}

/// Менеджер распознавания героев
pub struct RecognitionManager {
    state: Arc<Mutex<RecognitionState>>,
    result_sender: mpsc::Sender<Result<Vec<String>>>,
    result_receiver: Option<mpsc::Receiver<Result<Vec<String>>>>,
}

impl RecognitionManager {
    pub fn new() -> Result<Self> {
        let (result_sender, result_receiver) = mpsc::channel(1);
        
        Ok(Self {
            state: Arc::new(Mutex::new(RecognitionState::Idle)),
            result_sender,
            result_receiver: Some(result_receiver),
        })
    }
    
    /// Запускает распознавание героев
    pub fn start_recognition(&mut self) {
        if self.get_state() == RecognitionState::Recognizing {
            log::warn!("Распознавание уже запущено");
            return;
        }
        
        log::info!("Запуск распознавания героев");
        *self.state.lock().unwrap() = RecognitionState::Recognizing;
        
        let state_clone = self.state.clone();
        let sender_clone = self.result_sender.clone();
        
        let screenshot_result = take_screenshot();
        
        match screenshot_result {
            Ok(rgba_image) => {
                tokio::spawn(async move {
                    let mut engine = match SimpleRecognitionEngine::new() {
                        Ok(engine) => engine,
                        Err(e) => {
                            let error_msg = format!("Ошибка создания движка: {}", e);
                            log::error!("{}", error_msg);
                            *state_clone.lock().unwrap() = RecognitionState::Error(error_msg.clone());
                            let _ = sender_clone.send(Err(anyhow::anyhow!(error_msg))).await;
                            return;
                        }
                    };

                    match engine.recognize_heroes(&rgba_image).await {
                        Ok(heroes) => {
                            log::info!("Распознавание завершено: {:?}", heroes);
                            *state_clone.lock().unwrap() = RecognitionState::Finished(heroes.clone());
                            let _ = sender_clone.send(Ok(heroes)).await;
                        }
                        Err(e) => {
                            let error_msg = format!("Ошибка распознавания: {}", e);
                            log::error!("{}", error_msg);
                            *state_clone.lock().unwrap() = RecognitionState::Error(error_msg.clone());
                            let _ = sender_clone.send(Err(anyhow::anyhow!(error_msg))).await;
                        }
                    }
                });
            }
            Err(e) => {
                let error_msg = format!("Не удалось сделать скриншот: {}", e);
                log::error!("{}", error_msg);
                *self.state.lock().unwrap() = RecognitionState::Error(error_msg);
            }
        }
    }
    
    pub fn get_state(&self) -> RecognitionState {
        self.state.lock().unwrap().clone()
    }
    
    pub fn try_get_result(&mut self) -> Result<Option<Vec<String>>> {
        if let Some(ref mut receiver) = self.result_receiver {
            match receiver.try_recv() {
                Ok(result) => {
                    match result {
                        Ok(heroes) => Ok(Some(heroes)),
                        Err(e) => {
                            *self.state.lock().unwrap() = RecognitionState::Error(e.to_string());
                            Err(e)
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

fn take_screenshot() -> Result<RgbaImage> {
    let monitors = xcap::Monitor::all()?;
    if let Some(monitor) = monitors.first() {
        let image = monitor.capture_image()?;
        // Конвертация не требуется, т.к. xcap::Image это и есть image::RgbaImage при унификации версий
        Ok(image)
    } else {
        Err(anyhow::anyhow!("Не найдено доступных мониторов"))
    }
}