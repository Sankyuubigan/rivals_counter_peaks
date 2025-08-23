use crate::app::{RivalsApp, ActiveTab};
use eframe::{egui, Frame};
pub fn render(ctx: &egui::Context, app: &mut RivalsApp, _frame: &mut Frame) {
    egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
        ui.horizontal(|ui| {
            // --- Слайдер прозрачности (перемещен влево) ---
            ui.label("Прозрачность:");
            if ui.add(egui::Slider::new(&mut app.settings.window_opacity, 0.1..=1.0)).changed() {
                app.save_settings();
            }
            ui.add_space(10.0);
            
            // --- Переключатели режимов ---
            let is_normal_mode = app.ui_mode == crate::app::UIMode::Normal;
            if ui.selectable_label(is_normal_mode, "Обычный").clicked() && !is_normal_mode {
                app.ui_mode = crate::app::UIMode::Normal;
                if let Some(size) = app.normal_mode_size {
                    ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(size));
                }
            }
            let is_minimal_mode = app.ui_mode == crate::app::UIMode::Minimal;
            if ui.selectable_label(is_minimal_mode, "Минимальный").clicked() && !is_minimal_mode {
                if app.ui_mode == crate::app::UIMode::Normal {
                    // Сохраняем текущий размер окна перед переключением
                    let rect = ctx.available_rect();
                    app.normal_mode_size = Some(rect.size());
                }
                app.ui_mode = crate::app::UIMode::Minimal;
                ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(egui::vec2(1200.0, 80.0)));
            }
            ui.add_space(10.0);
            
            // --- Управление окном ---
            if ui.checkbox(&mut app.settings.always_on_top, "Поверх всех окон").changed() {
                app.save_settings();
            }
        });
    });
    
    // Добавляем панель с вкладками (только в обычном режиме)
    if app.ui_mode == crate::app::UIMode::Normal {
        egui::TopBottomPanel::top("tabs_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.selectable_value(&mut app.active_tab, ActiveTab::Main, "Основная");
                ui.selectable_value(&mut app.active_tab, ActiveTab::Settings, "Настройки");
                ui.selectable_value(&mut app.active_tab, ActiveTab::About, "О программе");
                ui.selectable_value(&mut app.active_tab, ActiveTab::Author, "Об авторе");
            });
        });
    }
}