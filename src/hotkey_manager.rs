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

        // Хоткей распознавания теперь обрабатывается через keyboard_monitor,
        // поэтому здесь его регистрировать не нужно.
        if matches!(action, Action::ToggleTabMode) {
             if manager.register(hotkey).is_ok() {
                info!("Хоткей для '{:?}' успешно зарегистрирован: {:?}", action, hotkey);
                id_to_action_map.insert(hotkey.id(), action.clone());
            } else {
                warn!("Не удалось зарегистрировать хоткей для '{:?}'", action);
            }
        }
    }
    
    // Запускаем фоновый поток для прослушивания событий, только если есть что слушать
    if !id_to_action_map.is_empty() {
        std::thread::spawn(move || {
            let receiver = GlobalHotKeyEvent::receiver();
            loop {
                if let Ok(event) = receiver.try_recv() {
                    if event.state == HotKeyState::Pressed {
                        if let Some(action) = id_to_action_map.get(&event.id) {
                            let app_action = match action {
                                Action::ToggleTabMode => HotkeyAction::ToggleTabMode(true),
                            };
                            if app_tx.blocking_send(app_action).is_err() {
                                warn!("Канал приложения для хоткеев закрыт. Поток завершается.");
                                break;
                            }
                        }
                    }
                }
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
        });
    } else {
        info!("Нет хоткеев для регистрации в global_hotkey, поток не запущен.");
    }
    
    Ok(())
}