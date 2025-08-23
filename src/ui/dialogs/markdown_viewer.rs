use eframe::egui;
/// Простой рендерер Markdown для `egui`.
pub fn render_markdown(markdown_text: &str, ui: &mut egui::Ui) {
    egui::ScrollArea::vertical().show(ui, |ui| {
        for line in markdown_text.lines() {
            if line.starts_with("# ") {
                ui.heading(line.strip_prefix("# ").unwrap_or(line));
            } else if line.starts_with("## ") {
                ui.label(
                    egui::RichText::new(line.strip_prefix("## ").unwrap_or(line))
                        .strong()
                        .size(18.0),
                );
            } else if line.starts_with("* ") {
                ui.horizontal(|ui| {
                    ui.label(" • ");
                    ui.label(line.strip_prefix("* ").unwrap_or(line));
                });
            } else if line.is_empty() {
                ui.add_space(10.0);
            } else {
                ui.label(line);
            }
        }
    });
}