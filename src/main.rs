mod app;
mod core_logic;
mod data_loader;
mod hotkey_config;
mod hotkey_manager;
mod image_loader;
mod models;
mod recognition;
mod settings_manager;
mod ui;
mod utils;
use app::RivalsApp;
use std::sync::Arc;
#[tokio::main]
async fn main() -> eframe::Result<()> {
    // Настраиваем логирование с включением DEBUG уровня
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Debug)
        .format_timestamp_secs()
        .init();
    
    log::info!("Запуск приложения Rust Rivals");
    log::debug!("Включен DEBUG уровень логирования");
    
    let native_options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([1000.0, 700.0])
            .with_min_inner_size([600.0, 400.0])
            .with_icon(load_icon()),
        ..Default::default()
    };
    
    match eframe::run_native(
        "Rust Rivals",
        native_options,
        Box::new(|cc| Box::new(RivalsApp::new(cc))),
    ) {
        Ok(_) => {
            log::info!("Приложение завершило работу корректно");
            Ok(())
        }
        Err(e) => {
            log::error!("Приложение завершило работу с ошибкой: {}", e);
            Err(e)
        }
    }
}
fn load_icon() -> Arc<eframe::egui::IconData> {
    let icon_path = "resources/logo.png";
    
    if !std::path::Path::new(icon_path).exists() {
        log::warn!("Иконка приложения не найдена по пути: {}", icon_path);
        return Arc::new(eframe::egui::IconData::default());
    }
    
    match image::open(icon_path) {
        Ok(img) => {
            log::info!("Иконка приложения успешно загружена");
            let rgba_image = img.to_rgba8();
            let (width, height) = rgba_image.dimensions();
            
            Arc::new(eframe::egui::IconData {
                rgba: rgba_image.into_raw(),
                width,
                height,
            })
        }
        Err(e) => {
            log::error!("Не удалось загрузить иконку приложения: {}", e);
            Arc::new(eframe::egui::IconData::default())
        }
    }
}