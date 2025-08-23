use crate::app::{RivalsApp, ActiveTab};
use eframe::egui;
pub fn render(ctx: &egui::Context, app: &RivalsApp) {
    // Отображаем панель только на основной вкладке
    if app.active_tab != ActiveTab::Main {
        return;
    }
    
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Рейтинг контрпиков");
        ui.separator();
        if app.selected_enemies.is_empty() {
            ui.label("Выберите врагов на панели справа для получения рекомендаций.");
        } else {
            let enemies_list: Vec<String> = app.selected_enemies.iter().cloned().collect();
            ui.label(format!("Рекомендации против: {}", enemies_list.join(", ")));
            ui.separator();
            ui.heading("Оптимальная команда");
            ui.horizontal(|ui| {
                for hero_name in &app.optimal_team {
                    if let Some(icon) = app.hero_icons.get(hero_name) {
                        ui.image(icon);
                    } else {
                        ui.label(hero_name);
                    }
                }
            });
            ui.separator();
            ui.heading("Полный рейтинг героев");
            egui::ScrollArea::vertical().show(ui, |ui| {
                for (hero_name, score) in &app.calculated_rating {
                    ui.horizontal(|ui| {
                         if let Some(icon) = app.hero_icons.get(hero_name) {
                            ui.image(icon);
                        }
                        ui.monospace(format!("{:<20}: {:.2}", hero_name, score));
                    });
                }
            });
        }
    });
}