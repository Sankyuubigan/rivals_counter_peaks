use crate::hotkey_config::{Action, HotkeyConfig};
use anyhow::Result;
use global_hotkey::{GlobalHotKeyEvent, GlobalHotKeyManager, HotKeyState};
use std::collections::HashMap;
use tokio::sync::mpsc;
use log::{info, warn};

#[derive(Debug, Clone, Copy)]
pub enum HotkeyAction {
    RecognizeHeroes,
}

// Структура больше не нужна, так как мы не будем хранить экземпляр.
// Вся логика перенесена в функцию `initialize`.

/// Инициализирует и запускает менеджер горячих клавиш в фоновом потоке.
pub fn initialize(app_tx: mpsc::Sender<HotkeyAction>, config: HotkeyConfig) -> Result<()> {
    let manager = GlobalHotKeyManager::new()?;
    let mut id_to_action_map = HashMap::new();
    let info_map = config.get_hotkey_info();
    
    for (action, info) in &info_map {
        let hotkey = info.hotkey;
        
        if manager.register(hotkey).is_ok() {
            info!("Хоткей для '{:?}' успешно зарегистрирован.", action);
            id_to_action_map.insert(hotkey.id(), action.clone());
        } else {
            warn!("Не удалось зарегистрировать хоткей для '{:?}'", action);
        }
    }
    
    // Запускаем фоновый поток для прослушивания событий
    std::thread::spawn(move || {
        let receiver = GlobalHotKeyEvent::receiver();
        loop {
            if let Ok(event) = receiver.try_recv() {
                if event.state == HotKeyState::Pressed {
                    if let Some(action) = id_to_action_map.get(&event.id) {
                        let app_action = match action {
                            Action::RecognizeHeroes => HotkeyAction::RecognizeHeroes,
                        };
                        // Используем блокирующую отправку, так как мы в обычном потоке
                        if app_tx.blocking_send(app_action).is_err() {
                            warn!("Канал приложения для хоткеев закрыт.");
                            break;
                        }
                    }
                }
            }
            // Небольшая пауза, чтобы не загружать процессор
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
    });
    
    Ok(())
}