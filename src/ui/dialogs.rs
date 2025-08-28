use crate::app::RivalsApp;
use crate::ui::markdown_viewer;
use eframe::egui;
use std::fs;
pub fn render(ctx: &egui::Context, app: &mut RivalsApp) {
    about_window(&mut app.show_about_window, ctx);
    author_window(&mut app.show_author_window, ctx);
}
fn about_window(is_open: &mut bool, ctx: &egui::Context) {
    let content = fs::read_to_string(crate::utils::get_absolute_path_string("resources/info/information_ru.md"))
        .unwrap_or_else(|e| format!("# Ошибка\nНе удалось загрузить файл: {}", e));
    egui::Window::new("О программе")
        .open(is_open)
        .collapsible(false)
        .resizable(true)
        .default_size([500.0, 400.0])
        .show(ctx, |ui| {
            markdown_viewer::render_markdown(&content, ui);
        });
}
fn author_window(is_open: &mut bool, ctx: &egui::Context) {
    let content = fs::read_to_string(crate::utils::get_absolute_path_string("resources/info/author_en.md"))
        .unwrap_or_else(|e| format!("# Error\nCould not load file: {}", e));
    
    egui::Window::new("Об авторе")
        .open(is_open)
        .collapsible(false)
        .resizable(true)
        .default_size([400.0, 300.0])
        .show(ctx, |ui| {
            markdown_viewer::render_markdown(&content, ui);
        });
}