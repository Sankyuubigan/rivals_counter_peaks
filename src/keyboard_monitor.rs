#[derive(Debug, Clone)]
pub enum KeyboardEvent {
    TabPressed,
    TabReleased,
    Recognize,
}

use std::sync::Arc;

#[cfg(target_os = "windows")]
pub struct KeyboardMonitor {
    event_sender: tokio::sync::mpsc::Sender<KeyboardEvent>,
    is_running: Arc<std::sync::atomic::AtomicBool>,
}

#[cfg(target_os = "windows")]
impl KeyboardMonitor {
    pub fn new(event_sender: tokio::sync::mpsc::Sender<KeyboardEvent>) -> Self {
        Self {
            event_sender,
            is_running: Arc::new(std::sync::atomic::AtomicBool::new(false)),
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
            let mut last_zero_state = false; // Состояние для клавиши '0'

            loop {
                if !running_flag.load(Ordering::Relaxed) {
                    break;
                }

                use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;
                const VK_TAB: i32 = 0x09;
                const VK_0: i32 = 0x30; // Virtual-Key Code для клавиши '0'

                // Проверка состояния TAB
                let is_tab_pressed = unsafe { (GetAsyncKeyState(VK_TAB) & (0x8000u16 as i16)) != 0 };

                if is_tab_pressed != last_tab_state {
                    let event = if is_tab_pressed {
                        KeyboardEvent::TabPressed
                    } else {
                        KeyboardEvent::TabReleased
                    };
                    if let Err(e) = sender.blocking_send(event) {
                        log::error!("Failed to send TAB event: {}", e);
                        break;
                    }
                    last_tab_state = is_tab_pressed;
                }
                
                // Проверка состояния '0' для распознавания (только если TAB зажат)
                if is_tab_pressed {
                    let is_zero_pressed = unsafe { (GetAsyncKeyState(VK_0) & (0x8000u16 as i16)) != 0 };
                    // Отправляем событие только при нажатии (rising edge)
                    if is_zero_pressed && !last_zero_state {
                        if let Err(e) = sender.blocking_send(KeyboardEvent::Recognize) {
                            log::error!("Failed to send Recognize event: {}", e);
                            break;
                        }
                    }
                    last_zero_state = is_zero_pressed;
                } else {
                    // Сбрасываем состояние '0', когда TAB отпущен
                    last_zero_state = false;
                }

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

#[cfg(not(target_os = "windows"))]
pub struct KeyboardMonitor;

#[cfg(not(target_os = "windows"))]
impl KeyboardMonitor {
    pub fn new(_event_sender: tokio::sync::mpsc::Sender<KeyboardEvent>) -> Self {
        Self
    }

    pub fn start(&self) {
        println!("❌ Keyboard monitoring not available on non-Windows systems");
    }

    pub fn stop(&self) {}
}