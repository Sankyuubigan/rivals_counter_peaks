use crate::hotkey_config::{Action, HotkeyConfig};
use anyhow::Result;
use global_hotkey::{GlobalHotKeyEvent, GlobalHotKeyManager, HotKeyState};
use std::collections::HashMap;
use tokio::sync::mpsc;
use log::{info, warn};

#[derive(Debug, Clone, Copy)]
pub enum HotkeyAction {
    RecognizeHeroes,
    ToggleTabMode(bool), // true = pressed, false = released
}

/// Инициализирует и запускает менеджер горячих клавиш в фоновом потоке.
/// Он будет отправлять сообщения в основной поток Iced через предоставленный канал.
pub fn initialize(app_tx: mpsc::Sender<HotkeyAction>, config: HotkeyConfig) -> Result<()> {
    // Создаем менеджер в основном потоке
    let manager = GlobalHotKeyManager::new()?;
    let mut id_to_action_map = HashMap::new();
    let info_map = config.get_hotkey_info();
    
    // Регистрируем хоткеи
    for (action, info) in &info_map {
        let hotkey = info.hotkey;

        if manager.register(hotkey).is_ok() {
            info!("Хоткей для '{:?}' успешно зарегистрирован: {:?}", action, hotkey);
            id_to_action_map.insert(hotkey.id(), action.clone());
        } else {
            warn!("Не удалось зарегистрировать хоткей для '{:?}'", action);
        }
    }
    
    // Запускаем фоновый поток для прослушивания событий
    std::thread::spawn(move || {
        // Получаем ресивер событий в этом потоке
        let receiver = GlobalHotKeyEvent::receiver();
        loop {
            // Используем `try_recv` для неблокирующей проверки
            if let Ok(event) = receiver.try_recv() {
                if event.state == HotKeyState::Pressed {
                    if let Some(action) = id_to_action_map.get(&event.id) {
                        let app_action = match action {
                            Action::RecognizeHeroes => HotkeyAction::RecognizeHeroes,
                            Action::ToggleTabMode => HotkeyAction::ToggleTabMode(true),
                        };
                        // Используем `blocking_send`, так как мы в синхронном потоке,
                        // а канал `mpsc` из `tokio`
                        if app_tx.blocking_send(app_action).is_err() {
                            warn!("Канал приложения для хоткеев закрыт. Поток завершается.");
                            break; // Выходим из цикла, если канал закрыт
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