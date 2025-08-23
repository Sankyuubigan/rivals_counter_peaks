use crate::app::RivalsApp;
use crate::hotkey_config::{Action, HotkeyConfig};
use eframe::egui;
use global_hotkey::hotkey::{Code, HotKey, Modifiers};
#[derive(Default)]
struct SettingsWindowState {
    temp_hotkey_config: HotkeyConfig,
    capturing_for_action: Option<Action>,
}
impl SettingsWindowState {
    fn new(initial_config: &HotkeyConfig) -> Self {
        Self {
            temp_hotkey_config: initial_config.clone(),
            capturing_for_action: None,
        }
    }
}
thread_local! {
    static SETTINGS_STATE: std::cell::RefCell<Option<SettingsWindowState>> = std::cell::RefCell::new(None);
}
pub fn render(ctx: &egui::Context, app: &mut RivalsApp) {
    if app.show_settings_window && SETTINGS_STATE.with(|s| s.borrow().is_none()) {
        SETTINGS_STATE.with(|s| {
            *s.borrow_mut() = Some(SettingsWindowState::new(&app.settings.hotkeys));
        });
    }
    if !app.show_settings_window && SETTINGS_STATE.with(|s| s.borrow().is_some()) {
        SETTINGS_STATE.with(|s| { *s.borrow_mut() = None; });
        return;
    }
    if !app.show_settings_window {
        return;
    }
    let mut is_open = app.show_settings_window;
    egui::Window::new("Настройки")
        .open(&mut is_open)
        .collapsible(false)
        .resizable(true)
        .default_size([500.0, 300.0])
        .show(ctx, |ui| {
            SETTINGS_STATE.with(|s| {
                if let Some(mut state) = s.borrow_mut().as_mut() {
                    render_content(ui, app, &mut state);
                }
            });
        });
    app.show_settings_window = is_open;
}
fn render_content(ui: &mut egui::Ui, app: &mut RivalsApp, state: &mut SettingsWindowState) {
    ui.heading("Горячие клавиши");
    ui.separator();
    
    // Проверяем, находимся ли мы в режиме захвата хоткея
    if let Some(action_to_capture) = &state.capturing_for_action {
        // В режиме захвата хоткея блокируем навигацию Tab
        app.prevent_tab_navigation = true;
        
        // Перехватываем события клавиатуры, включая Tab
        if let Some(key_event) = ui.ctx().input(|i| {
            i.events.iter().find_map(|e| match e {
                egui::Event::Key { key, pressed: true, .. } => {
                    // Позволяем использовать Tab как хоткей
                    if *key == egui::Key::Tab {
                        Some((*key, i.modifiers))
                    } else {
                        Some((*key, i.modifiers))
                    }
                }
                _ => None,
            })
        }) {
            if let Some(new_hotkey) = key_to_hotkey(key_event.0, key_event.1) {
                if let Some(info) = state.temp_hotkey_config.actions.get_mut(action_to_capture) {
                    *info = crate::hotkey_config::SerializableHotkey::from(&new_hotkey);
                }
                state.capturing_for_action = None;
                // Выходим из режима захвата хоткея
                app.prevent_tab_navigation = false;
            }
        }
    } else {
        // Если не в режиме захвата, убедимся что Tab не блокируется
        app.prevent_tab_navigation = false;
    }
    
    egui::Grid::new("hotkeys_grid").num_columns(3).spacing([20.0, 10.0]).show(ui, |ui| {
        // Клонируем ключи, чтобы избежать проблем с заимствованием
        let actions: Vec<_> = state.temp_hotkey_config.actions.keys().cloned().collect();
        for action in actions {
            let info = state.temp_hotkey_config.actions.get(&action).unwrap();
            ui.label(get_action_description(&action));
            let hotkey_text = if Some(&action) == state.capturing_for_action.as_ref() {
                "Нажмите клавиши...".to_string()
            } else {
                format_serializable_hotkey_for_display(info)
            };
            ui.label(egui::RichText::new(&hotkey_text).monospace());
            if ui.button("Изменить").clicked() {
                state.capturing_for_action = Some(action.clone());
                // Входим в режим захвата хоткея
                app.prevent_tab_navigation = true;
            }
            ui.end_row();
        }
    });
    ui.add_space(20.0);
    ui.separator();
    ui.horizontal(|ui| {
        if ui.button("Применить").clicked() {
            app.settings.hotkeys = state.temp_hotkey_config.clone();
            app.save_settings();
            if let Err(e) = app.hotkey_manager.update_hotkeys(&app.settings.hotkeys) {
                log::error!("Не удалось обновить хоткеи: {}", e);
            }
            // Выходим из режима захвата хоткея
            app.prevent_tab_navigation = false;
        }
        if ui.button("OK").clicked() {
            app.settings.hotkeys = state.temp_hotkey_config.clone();
            app.save_settings();
            if let Err(e) = app.hotkey_manager.update_hotkeys(&app.settings.hotkeys) {
                log::error!("Не удалось обновить хоткеи: {}", e);
            }
            app.show_settings_window = false;
            // Выходим из режима захвата хоткея
            app.prevent_tab_navigation = false;
        }
        if ui.button("Отмена").clicked() {
            app.show_settings_window = false;
            // Выходим из режима захвата хоткея
            app.prevent_tab_navigation = false;
        }
    });
}
fn get_action_description(action: &Action) -> String {
    match action {
        Action::RecognizeHeroes => "Распознать героев на экране".to_string(),
    }
}
fn format_serializable_hotkey_for_display(hotkey: &crate::hotkey_config::SerializableHotkey) -> String {
    let mut parts = Vec::new();
    for m_str in &hotkey.mods {
        match m_str.as_str() {
            "control" => parts.push("Ctrl"),
            "shift" => parts.push("Shift"),
            "alt" => parts.push("Alt"),
            "super" => parts.push("Win"),
            _ => {}
        }
    }
    parts.push(&hotkey.key);
    parts.join(" + ")
}
fn key_to_hotkey(key: egui::Key, modifiers: egui::Modifiers) -> Option<HotKey> {
    let mut hotkey_mods = Modifiers::empty();
    if modifiers.ctrl { hotkey_mods.insert(Modifiers::CONTROL); }
    if modifiers.shift { hotkey_mods.insert(Modifiers::SHIFT); }
    if modifiers.alt { hotkey_mods.insert(Modifiers::ALT); }
    if modifiers.mac_cmd || modifiers.command { hotkey_mods.insert(Modifiers::SUPER); }
    egui_key_to_code(key).map(|code| HotKey::new(Some(hotkey_mods), code))
}
fn egui_key_to_code(key: egui::Key) -> Option<Code> {
    use egui::Key;
    use global_hotkey::hotkey::Code;
    match key {
        Key::A => Some(Code::KeyA),
        Key::B => Some(Code::KeyB),
        Key::C => Some(Code::KeyC),
        Key::D => Some(Code::KeyD),
        Key::E => Some(Code::KeyE),
        Key::F => Some(Code::KeyF),
        Key::G => Some(Code::KeyG),
        Key::H => Some(Code::KeyH),
        Key::I => Some(Code::KeyI),
        Key::J => Some(Code::KeyJ),
        Key::K => Some(Code::KeyK),
        Key::L => Some(Code::KeyL),
        Key::M => Some(Code::KeyM),
        Key::N => Some(Code::KeyN),
        Key::O => Some(Code::KeyO),
        Key::P => Some(Code::KeyP),
        Key::Q => Some(Code::KeyQ),
        Key::R => Some(Code::KeyR),
        Key::S => Some(Code::KeyS),
        Key::T => Some(Code::KeyT),
        Key::U => Some(Code::KeyU),
        Key::V => Some(Code::KeyV),
        Key::W => Some(Code::KeyW),
        Key::X => Some(Code::KeyX),
        Key::Y => Some(Code::KeyY),
        Key::Z => Some(Code::KeyZ),
        Key::Num0 => Some(Code::Digit0),
        Key::Num1 => Some(Code::Digit1),
        Key::Num2 => Some(Code::Digit2),
        Key::Num3 => Some(Code::Digit3),
        Key::Num4 => Some(Code::Digit4),
        Key::Num5 => Some(Code::Digit5),
        Key::Num6 => Some(Code::Digit6),
        Key::Num7 => Some(Code::Digit7),
        Key::Num8 => Some(Code::Digit8),
        Key::Num9 => Some(Code::Digit9),
        Key::F1 => Some(Code::F1),
        Key::F2 => Some(Code::F2),
        Key::F3 => Some(Code::F3),
        Key::F4 => Some(Code::F4),
        Key::F5 => Some(Code::F5),
        Key::F6 => Some(Code::F6),
        Key::F7 => Some(Code::F7),
        Key::F8 => Some(Code::F8),
        Key::F9 => Some(Code::F9),
        Key::F10 => Some(Code::F10),
        Key::F11 => Some(Code::F11),
        Key::F12 => Some(Code::F12),
        Key::Escape => Some(Code::Escape),
        Key::Tab => Some(Code::Tab), // Добавлена поддержка Tab
        Key::Space => Some(Code::Space),
        Key::Enter => Some(Code::Enter),
        Key::Backspace => Some(Code::Backspace),
        _ => None,
    }
}