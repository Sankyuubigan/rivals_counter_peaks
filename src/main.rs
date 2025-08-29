use iced::{window, Application, Settings};
use log::LevelFilter;
use rust_rivals::*;

#[tokio::main]
async fn main() -> iced::Result {
    // Настраиваем логирование
    env_logger::Builder::from_default_env()
        .filter_level(LevelFilter::Info)
        .filter_module("rust_rivals", LevelFilter::Debug)
        .filter_module("wgpu_core", LevelFilter::Warn)
        .filter_module("wgpu_hal", LevelFilter::Warn)
        .filter_module("iced_wgpu", LevelFilter::Warn) // Уменьшаем "спам" в логах от рендера
        .format_timestamp_secs()
        .init();

    log::info!("Запуск приложения Rust Rivals - Iced версия");
    log::debug!("Включен DEBUG уровень логирования для rust_rivals.");

    // Загружаем иконку приложения из PNG файла
    let icon = match image::open(crate::utils::get_absolute_path("resources/logo.png")) {
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
    crate::ui::iced_app::IcedApp::run(Settings {
        window: window::Settings {
            size: iced::Size::new(1024.0, 768.0),
            icon,
            ..window::Settings::default()
        },
        ..Settings::default()
    })
}