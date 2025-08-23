use crate::app::RivalsApp;
use crate::recognition::RecognitionState;
use eframe::egui;
pub fn render(ctx: &egui::Context, app: &mut RivalsApp) {
    // В минимальном режиме всегда показываем основной контент, игнорируя вкладки
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.horizontal(|ui| {
            // --- Левая часть: Рекомендации ---
            ui.vertical(|ui| {
                ui.label("Рекомендации:");
                ui.horizontal(|ui| {
                    if app.optimal_team.is_empty() {
                        ui.label("-");
                    }
                    for hero_name in &app.optimal_team {
                        if let Some(icon) = app.hero_icons.get(hero_name) {
                            ui.image(icon).on_hover_text(hero_name);
                        } else {
                            ui.label(hero_name);
                        }
                    }
                });
            });
            ui.separator();
            // --- Правая часть: Враги и управление ---
            ui.vertical(|ui| {
                ui.label("Выбранные враги:");
                ui.horizontal(|ui| {
                    if app.selected_enemies.is_empty() {
                        ui.label("-");
                    }
                    for hero_name in &app.selected_enemies {
                        if let Some(icon) = app.hero_icons.get(hero_name) {
                            ui.image(icon).on_hover_text(hero_name);
                        } else {
                            ui.label(hero_name);
                        }
                    }
                });
            });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                // --- Кнопка и статус распознавания ---
                let is_recognizing = app.recognition_manager.as_ref()
                    .map(|m| m.get_state() == RecognitionState::Recognizing)
                    .unwrap_or(false);
                    
                let button_text = if is_recognizing {
                    "Распознавание..."
                } else {
                    "Распознать"
                };
                
                if ui.add_enabled(!is_recognizing, egui::Button::new(button_text)).clicked() {
                    app.start_recognition();
                }
                
                match app.recognition_manager.as_ref().map(|m| m.get_state()) {
                    Some(RecognitionState::Recognizing) => {
                        ui.spinner();
                    }
                    Some(RecognitionState::Finished(h)) => {
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
            });
        });
    });
}