use crate::hotkey_config::HotkeyConfig;
use anyhow::{Context, Result};
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AppSettings {
    pub hotkeys: HotkeyConfig,
    pub always_on_top: bool,
    pub window_opacity: f32,
}
impl Default for AppSettings {
    fn default() -> Self {
        Self {
            hotkeys: HotkeyConfig::default(),
            always_on_top: false,
            window_opacity: 1.0,
        }
    }
}
/// Возвращает путь к файлу настроек.
fn get_settings_path() -> Result<PathBuf> {
    if let Some(proj_dirs) = ProjectDirs::from("com", "RustRivals", "RustRivals") {
        let config_dir = proj_dirs.config_dir();
        fs::create_dir_all(config_dir)
            .with_context(|| format!("Не удалось создать директорию настроек: {:?}", config_dir))?;
        Ok(config_dir.join("settings.json"))
    } else {
        Err(anyhow::anyhow!("Не удалось определить директорию для настроек."))
    }
}
/// Загружает настройки из файла.
pub fn load_settings() -> Result<AppSettings> {
    let path = get_settings_path()?;
    if path.exists() {
        let content = fs::read_to_string(&path)
            .with_context(|| format!("Не удалось прочитать файл настроек: {:?}", path))?;
        let settings: AppSettings = serde_json::from_str(&content)
            .with_context(|| format!("Не удалось распарсить JSON из файла: {:?}", path))?;
        log::info!("Настройки успешно загружены из {:?}", path);
        Ok(settings)
    } else {
        log::info!("Файл настроек не найден, будут использованы значения по умолчанию.");
        Ok(AppSettings::default())
    }
}
/// Сохраняет настройки в файл.
pub fn save_settings(settings: &AppSettings) -> Result<()> {
    let path = get_settings_path()?;
    let content = serde_json::to_string_pretty(settings)
        .context("Не удалось сериализовать настройки в JSON.")?;
    fs::write(&path, content)
        .with_context(|| format!("Не удалось записать настройки в файл: {:?}", path))?;
    log::info!("Настройки успешно сохранены в {:?}", path);
    Ok(())
}