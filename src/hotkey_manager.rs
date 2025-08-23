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
pub struct HotkeyManager {
    manager: GlobalHotKeyManager,
    id_to_action_map: HashMap<u32, Action>,
    hotkeys: Vec<global_hotkey::hotkey::HotKey>,
    app_tx: mpsc::Sender<HotkeyAction>,
}
impl HotkeyManager {
    pub fn new(app_tx: mpsc::Sender<HotkeyAction>, config: HotkeyConfig) -> Result<Self> {
        let manager = GlobalHotKeyManager::new()?;
        let mut id_to_action_map = HashMap::new();
        let mut hotkeys = Vec::new();
        let info_map = config.get_hotkey_info();
        
        for (action, info) in &info_map {
            let hotkey = info.hotkey;
            
            // Пытаемся зарегистрировать хоткей
            match manager.register(hotkey) {
                Ok(_) => {
                    info!("Хоткей для '{:?}' успешно зарегистрирован.", action);
                    id_to_action_map.insert(hotkey.id(), action.clone());
                    hotkeys.push(hotkey);
                }
                Err(e) => {
                    warn!("Не удалось зарегистрировать хоткей для '{:?}': {}. Пробуем отменить регистрацию и зарегистрировать заново.", action, e);
                    
                    // Пытаемся отменить регистрацию всех хоткеев и начать заново
                    if let Err(unregister_err) = manager.unregister_all(&hotkeys) {
                        warn!("Не удалось отменить регистрацию хоткеев: {}", unregister_err);
                    }
                    hotkeys.clear();
                    id_to_action_map.clear();
                    
                    // Пытаемся зарегистрировать хоткей снова
                    match manager.register(hotkey) {
                        Ok(_) => {
                            info!("Хоткей для '{:?}' успешно зарегистрирован после повторной попытки.", action);
                            id_to_action_map.insert(hotkey.id(), action.clone());
                            hotkeys.push(hotkey);
                        }
                        Err(e2) => {
                            warn!("Не удалось зарегистрировать хоткей для '{:?}' после повторной попытки: {}", action, e2);
                            // Продолжаем работу без этого хоткея
                        }
                    }
                }
            }
        }
        
        let event_receiver = GlobalHotKeyEvent::receiver();
        let id_map_clone = id_to_action_map.clone();
        let app_tx_clone = app_tx.clone();
        tokio::spawn(async move {
            loop {
                if let Ok(event) = event_receiver.try_recv() {
                    if event.state == HotKeyState::Pressed {
                        if let Some(action) = id_map_clone.get(&event.id) {
                            let app_action = match action {
                                Action::RecognizeHeroes => HotkeyAction::RecognizeHeroes,
                            };
                            if app_tx_clone.send(app_action).await.is_err() {
                                warn!("Канал приложения для хоткеев закрыт.");
                                break;
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
            }
        });
        
        Ok(Self { manager, id_to_action_map, hotkeys, app_tx })
    }
    
    pub fn update_hotkeys(&mut self, new_config: &HotkeyConfig) -> Result<()> {
        // Сначала отменяем регистрацию всех текущих хоткеев
        if !self.hotkeys.is_empty() {
            if let Err(e) = self.manager.unregister_all(&self.hotkeys) {
                warn!("Не удалось отменить регистрацию хоткеев: {}", e);
            }
        }
        
        self.id_to_action_map.clear();
        self.hotkeys.clear();
        
        let info_map = new_config.get_hotkey_info();
        for (action, info) in &info_map {
            let hotkey = info.hotkey;
            
            match self.manager.register(hotkey) {
                Ok(_) => {
                    info!("Новый хоткей для '{:?}' успешно зарегистрирован.", action);
                    self.id_to_action_map.insert(hotkey.id(), action.clone());
                    self.hotkeys.push(hotkey);
                }
                Err(e) => {
                    warn!("Не удалось зарегистрировать новый хоткей для '{:?}': {}", action, e);
                    // Продолжаем работу без этого хоткея
                }
            }
        }
        
        Ok(())
    }
}