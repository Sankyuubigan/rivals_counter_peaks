use crate::app::{RivalsApp, ActiveTab};
use eframe::egui;
use std::fs;
use crate::ui::dialogs::markdown_viewer; // Импортируем markdown_viewer

pub fn render(ctx: &egui::Context, app: &mut RivalsApp) {
    // Отображаем содержимое только в обычном режиме
    if app.ui_mode != crate::app::UIMode::Normal {
        return;
    }
    
    match app.active_tab {
        ActiveTab::Main => {
            // Основной контент отображается в left_panel и right_panel
        }
        ActiveTab::Settings => {
            render_settings_tab(ctx, app);
        }
        ActiveTab::About => {
            render_about_tab(ctx, app);
        }
        ActiveTab::Author => {
            render_author_tab(ctx, app);
        }
    }
}

fn render_settings_tab(ctx: &egui::Context, app: &mut RivalsApp) {
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Настройки");
        ui.separator();
        
        ui.heading("Горячие клавиши");
        ui.separator();
        
        // Отображаем текущие настройки хоткеев
        let info_map = app.settings.hotkeys.get_hotkey_info();
        for (action, info) in info_map {
            ui.horizontal(|ui| {
                let action_desc = match action {
                    crate::hotkey_config::Action::RecognizeHeroes => "Распознать героев на экране",
                };
                ui.label(action_desc);
                ui.label(": ");
                
                let hotkey_text = format_hotkey_for_display(&info.hotkey);
                ui.label(egui::RichText::new(&hotkey_text).monospace());
                
                if ui.button("Изменить").clicked() {
                    app.show_settings_window = true;
                    app.active_tab = ActiveTab::Settings;
                }
            });
        }
        
        ui.add_space(20.0);
        ui.separator();
        
        ui.heading("Окно приложения");
        ui.separator();
        
        if ui.checkbox(&mut app.settings.always_on_top, "Поверх всех окон").changed() {
            app.save_settings();
        }
        
        ui.horizontal(|ui| {
            ui.label("Прозрачность окна:");
            if ui.add(egui::Slider::new(&mut app.settings.window_opacity, 0.1..=1.0)).changed() {
                app.save_settings();
            }
        });
    });
}

fn render_about_tab(ctx: &egui::Context, _app: &mut RivalsApp) {
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("О программе");
        ui.separator();
        
        let content = fs::read_to_string(crate::utils::get_absolute_path_string("resources/info/information_ru.md"))
            .unwrap_or_else(|e| format!("# Ошибка\nНе удалось загрузить файл: {}", e));
            
        markdown_viewer::render_markdown(&content, ui);
    });
}

fn render_author_tab(ctx: &egui::Context, _app: &mut RivalsApp) {
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Об авторе");
        ui.separator();
        
        // Исправляем путь к файлу - теперь ищем author_ru.md вместо author_en.md
        let content = fs::read_to_string(crate::utils::get_absolute_path_string("resources/info/author_ru.md"))
            .unwrap_or_else(|e| format!("# Ошибка\nНе удалось загрузить файл: {}", e));
            
        markdown_viewer::render_markdown(&content, ui);
    });
}

fn format_hotkey_for_display(hotkey: &global_hotkey::hotkey::HotKey) -> String {
    let mut parts = Vec::new();
    
    // Используем метод matches для проверки каждого модификатора
    if hotkey.matches(&global_hotkey::hotkey::Modifiers::CONTROL, &global_hotkey::hotkey::Code::Unidentified) {
        parts.push("Ctrl");
    }
    if hotkey.matches(&global_hotkey::hotkey::Modifiers::SHIFT, &global_hotkey::hotkey::Code::Unidentified) {
        parts.push("Shift");
    }
    if hotkey.matches(&global_hotkey::hotkey::Modifiers::ALT, &global_hotkey::hotkey::Code::Unidentified) {
        parts.push("Alt");
    }
    if hotkey.matches(&global_hotkey::hotkey::Modifiers::SUPER, &global_hotkey::hotkey::Code::Unidentified) {
        parts.push("Win");
    }
    
    // Получаем ключ через метод matches
    let key_str = format!("{:?}", hotkey);
    // Извлекаем ключ из отладочного формата
    // Формат обычно такой: HotKey { mods: Modifiers(SHIFT | CONTROL), key: KeyX, id: 12345 }
    let key_parts: Vec<&str> = key_str.split(',').collect();
    let mut key = "KeyX".to_string(); // значение по умолчанию
    
    if key_parts.len() > 1 {
        let key_part = key_parts[1].trim();
        if let Some(key_start) = key_part.find("key:") {
            let key_value = key_part[key_start + 4..].trim();
            if let Some(key_end) = key_value.find(',') {
                key = key_value[..key_end].trim().to_string();
            } else {
                if let Some(key_end) = key_value.find('}') {
                    key = key_value[..key_end].trim().to_string();
                }
            }
        }
    }
    
    // Преобразуем в читаемый формат
    let key_name = match key.as_str() {
        "KeyA" => "A",
        "KeyB" => "B",
        "KeyC" => "C",
        "KeyD" => "D",
        "KeyE" => "E",
        "KeyF" => "F",
        "KeyG" => "G",
        "KeyH" => "H",
        "KeyI" => "I",
        "KeyJ" => "J",
        "KeyK" => "K",
        "KeyL" => "L",
        "KeyM" => "M",
        "KeyN" => "N",
        "KeyO" => "O",
        "KeyP" => "P",
        "KeyQ" => "Q",
        "KeyR" => "R",
        "KeyS" => "S",
        "KeyT" => "T",
        "KeyU" => "U",
        "KeyV" => "V",
        "KeyW" => "W",
        "KeyX" => "X",
        "KeyY" => "Y",
        "KeyZ" => "Z",
        "Digit0" => "0",
        "Digit1" => "1",
        "Digit2" => "2",
        "Digit3" => "3",
        "Digit4" => "4",
        "Digit5" => "5",
        "Digit6" => "6",
        "Digit7" => "7",
        "Digit8" => "8",
        "Digit9" => "9",
        "F1" => "F1",
        "F2" => "F2",
        "F3" => "F3",
        "F4" => "F4",
        "F5" => "F5",
        "F6" => "F6",
        "F7" => "F7",
        "F8" => "F8",
        "F9" => "F9",
        "F10" => "F10",
        "F11" => "F11",
        "F12" => "F12",
        "Escape" => "Esc",
        "Tab" => "Tab",
        "Space" => "Space",
        "Enter" => "Enter",
        "Backspace" => "Backspace",
        _ => &key_str,
    };
    
    parts.push(key_name);
    parts.join(" + ")
}