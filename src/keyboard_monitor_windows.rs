use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;
use tokio::sync::mpsc;
use std::sync::Arc;

use std::sync::atomic;

use crate::keyboard_monitor;

pub struct KeyboardMonitor {
    event_sender: mpsc::Sender<keyboard_monitor::KeyboardEvent>,
    is_running: Arc<atomic::AtomicBool>,
}

impl KeyboardMonitor {
    pub fn new(event_sender: mpsc::Sender<keyboard_monitor::KeyboardEvent>) -> Self {
        Self {
            event_sender,
            is_running: Arc::new(atomic::AtomicBool::new(false)),
        }
    }

    pub fn start(&self) {
        use std::sync::atomic::Ordering;

        if self.is_running.load(Ordering::Relaxed) {
            log::warn!("Keyboard monitor is already running");
            return;
        }

        self.is_running.store(true, Ordering::Relaxed);

        let sender = self.event_sender.clone();
        let running_flag = Arc::clone(&self.is_running);

        std::thread::spawn(move || {
            log::info!("Keyboard monitor thread started");

            let mut last_tab_state = false;
            const VK_TAB: i32 = 0x09;

            loop {
                if !running_flag.load(Ordering::Relaxed) {
                    break;
                }

                // Проверяем состояние клавиши TAB
                let is_tab_pressed = unsafe {
                    // GetAsyncKeyState возвращает старшее бит, если клавиша нажата
                    let state = GetAsyncKeyState(VK_TAB);
                    (state & (0x8000u16 as i16)) != 0
                };

                // Отправляем событие только при изменении состояния
                if is_tab_pressed != last_tab_state {
                    let event = if is_tab_pressed {
                        keyboard_monitor::KeyboardEvent::TabPressed
                    } else {
                        keyboard_monitor::KeyboardEvent::TabReleased
                    };

                    if let Err(e) = sender.blocking_send(event) {
                        log::error!("Failed to send keyboard event: {}", e);
                        break;
                    }

                    last_tab_state = is_tab_pressed;
                }

                // Небольшая пауза, чтобы не загружать процессор
                std::thread::sleep(std::time::Duration::from_millis(50));
            }

            log::info!("Keyboard monitor thread stopped");
        });
    }

    pub fn stop(&self) {
        use std::sync::atomic::Ordering;
        self.is_running.store(false, Ordering::Relaxed);
    }
}