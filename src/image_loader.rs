use crate::utils::get_absolute_path_string;
use eframe::egui;
use std::collections::HashMap;
use log::info;
pub fn load_hero_icons(
hero_names: &[String],
ctx: &egui::Context,
) -> HashMap<String, egui::TextureHandle> {
let mut icons = HashMap::new();
// Ищем иконки только в resources/heroes_icons/
let resources_dir = get_absolute_path_string("resources/heroes_icons");
info!("Ищем иконки героев в директории: {}", resources_dir);
// Целевой размер иконок
const ICON_SIZE: u32 = 32;
for name in hero_names {
let filename_base = name.to_lowercase().replace(' ', "_").replace('&', "and");
// Ищем первую иконку (с суффиксом _1.png)
let path = get_absolute_path_string(&format!("resources/heroes_icons/{}_1.png", filename_base));
match image::open(&path) {
Ok(img) => {
// Масштабируем изображение до нужного размера
let resized_img = img.resize_exact(ICON_SIZE, ICON_SIZE, image::imageops::FilterType::Lanczos3);
let rgba_image = resized_img.to_rgba8();
let pixels = rgba_image.as_flat_samples();
let color_image = egui::ColorImage::from_rgba_unmultiplied([ICON_SIZE as usize, ICON_SIZE as usize], pixels.as_slice());
let texture_handle = ctx.load_texture(
format!("hero-icon-{}", name),
color_image,
Default::default(),
);
icons.insert(name.clone(), texture_handle);
// info!("Загружена иконка для героя: {}", name); // Закомментировано
}
Err(_) => {
info!("НЕ НАЙДЕНА ИКОНКА ДЛЯ ГЕРОЯ: {} - ОЖИДАЛСЯ ПУТЬ: {}", name, path);
}
}
}
info!("Загружено {} иконок героев.", icons.len());
icons
}