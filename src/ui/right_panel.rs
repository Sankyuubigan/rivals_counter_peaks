use crate::app::{RivalsApp, ActiveTab};
use eframe::egui;
use log::info;
const ICON_SIZE: egui::Vec2 = egui::vec2(32.0, 32.0);  // Уменьшаем размер иконок
const COLUMNS: usize = 5;  // 5 столбцов как требовалось
/// Отрисовывает правую панель и возвращает `true`, если выбор изменился.
pub fn render(ctx: &egui::Context, app: &mut RivalsApp) -> bool {
    // Отображаем панель только на основной вкладке
    if app.active_tab != ActiveTab::Main {
        return false;
    }
    
    let mut selection_changed = false;
    egui::SidePanel::right("right_panel")
        .resizable(true)
        .default_width((ICON_SIZE.x + 8.0) * COLUMNS as f32 + 30.0)  // Увеличиваем ширину для 5 столбцов
        .min_width(250.0)
        .show(ctx, |ui| {
            ui.heading("Выбор вражеской команды");
            ui.add_space(5.0);
            
            // --- Панель управления ---
            ui.horizontal(|ui| {
                // --- Кнопка распознавания ---
                let is_recognizing = app.recognition_manager.as_ref()
                    .map(|m| m.get_state() == crate::recognition::RecognitionState::Recognizing)
                    .unwrap_or(false);
                    
                let button_text = if is_recognizing {
                    "Распознавание..."
                } else {
                    "Распознать героев"
                };
                
                if ui.add_enabled(!is_recognizing, egui::Button::new(button_text)).clicked() {
                    app.start_recognition();
                }
                
                match app.recognition_manager.as_ref().map(|m| m.get_state()) {
                    Some(crate::recognition::RecognitionState::Recognizing) => {
                        ui.spinner();
                    }
                    Some(crate::recognition::RecognitionState::Finished(h)) => {
                        ui.colored_label(egui::Color32::GREEN, format!("Найдено: {}", h.len()));
                    }
                    _ => {}
                }
                
                // Показываем ошибку, если она есть
                if let Some(ref manager) = app.recognition_manager {
                    if let Some(error) = manager.get_last_error() {
                        ui.colored_label(egui::Color32::RED, "Ошибка").on_hover_text(error.to_string());
                    }
                }
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button("Очистить всё").clicked() {
                        app.selected_enemies.clear();
                        selection_changed = true;
                    }
                    if ui.button("Копировать состав").clicked() {
                        let team_str = app.optimal_team.join(", ");
                        if let Err(e) = app.clipboard.set_text(team_str.clone()) {
                            log::error!("Не удалось скопировать в буфер обмена: {}", e);
                        } else {
                            info!("Скопировано в буфер: {}", team_str);
                        }
                    }
                });
            });
            ui.separator();
            // --- Сетка героев ---
            egui::ScrollArea::vertical().show(ui, |ui| {
                // Используем Grid вместо horizontal_wrapped для точного контроля столбцов
                egui::Grid::new("heroes_grid")
                    .spacing(egui::vec2(5.0, 5.0))  // Отступы между иконками
                    .min_col_width(ICON_SIZE.x + 5.0)
                    .show(ui, |ui| {
                        for (index, hero_name) in app.all_hero_names.iter().enumerate() {
                            let is_selected = app.selected_enemies.contains(hero_name);
                            
                            if let Some(icon) = app.hero_icons.get(hero_name) {
                                let image_button = egui::ImageButton::new(icon)
                                    .selected(is_selected);
                                
                                if ui.add(image_button).clicked() {
                                    if is_selected { 
                                        app.selected_enemies.remove(hero_name); 
                                    } else {
                                        // Если уже выбрано 6 героев, удаляем самого первого
                                        if app.selected_enemies.len() >= 6 {
                                            let first_hero_name = app.selected_enemies.iter().next().cloned();
                                            if let Some(to_remove) = first_hero_name {
                                                app.selected_enemies.remove(&to_remove);
                                            }
                                        }
                                        app.selected_enemies.insert(hero_name.clone()); 
                                    }
                                    selection_changed = true;
                                }
                            } else {
                                if ui.selectable_label(is_selected, hero_name).clicked() {
                                    if is_selected { 
                                        app.selected_enemies.remove(hero_name); 
                                    } else {
                                        // Если уже выбрано 6 героев, удаляем самого первого
                                        if app.selected_enemies.len() >= 6 {
                                            let first_hero_name = app.selected_enemies.iter().next().cloned();
                                            if let Some(to_remove) = first_hero_name {
                                                app.selected_enemies.remove(&to_remove);
                                            }
                                        }
                                        app.selected_enemies.insert(hero_name.clone()); 
                                    }
                                    selection_changed = true;
                                }
                            }
                            
                            // Переходим на новую строку каждые COLUMNS элементов
                            if (index + 1) % COLUMNS == 0 {
                                ui.end_row();
                            }
                        }
                        
                        // Закрываем последнюю строку если нужно
                        if app.all_hero_names.len() % COLUMNS != 0 {
                            ui.end_row();
                        }
                    });
            });
        });
    selection_changed
}