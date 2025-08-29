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

use iced::{window, Application, Settings};
use log::LevelFilter;

#[tokio::main]
async fn main() -> iced::Result {
    // Настраиваем логирование
    env_logger::Builder::from_default_env()
        .filter_level(LevelFilter::Info)
        .filter_module("rust_rivals", LevelFilter::Debug)
        .filter_module("wgpu_core", LevelFilter::Warn)
        .filter_module("wgpu_hal", LevelFilter::Warn)
        .format_timestamp_secs()
        .init();

    log::info!("Запуск приложения Rust Rivals - Iced версия");
    log::debug!("Включен DEBUG уровень логирования для rust_rivals.");

    // Загружаем иконку приложения из PNG файла
    let icon = match image::open("resources/logo.png") {
        Ok(img) => {
            let rgba_image = img.to_rgba8();
            let (width, height) = rgba_image.dimensions();
            match window::icon::from_rgba(rgba_image.into_raw(), width, height) {
                Ok(icon) => Some(icon),
                Err(e) => {
                    log::warn!("Не удалось создать иконку из данных: {}", e);
                    None
                }
            }
        }
        Err(e) => {
            log::warn!("Не удалось загрузить файл иконки 'resources/logo.png': {}", e);
            None
        }
    };
    
    // Запускаем Iced приложение с нашими настройками.
    ui::iced_app::IcedApp::run(Settings {
        window: window::Settings {
            icon,
            ..window::Settings::default()
        },
        ..Settings::default()
    })
}