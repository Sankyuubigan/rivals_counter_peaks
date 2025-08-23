use crate::hotkey_manager::{HotkeyAction, HotkeyManager};
use crate::models::{AllHeroesData, HeroRoles};
use crate::recognition::RecognitionManager;
use crate::settings_manager::{self, AppSettings};
use crate::{core_logic, data_loader, hotkey_manager, image_loader, ui};
use eframe::egui;
use std::collections::{HashMap, HashSet};
use tokio::sync::mpsc;
use log::{info, error, warn};

#[derive(PartialEq, Debug)]
pub enum UIMode {
    Normal,
    Minimal,
}

pub struct RivalsApp {
    // Данные
    pub all_heroes_data: AllHeroesData,
    pub hero_roles: HeroRoles,
    pub all_hero_names: Vec<String>,
    pub hero_icons: HashMap<String, egui::TextureHandle>,
    // Состояние
    pub selected_enemies: HashSet<String>,
    pub calculated_rating: Vec<(String, f32)>,
    pub optimal_team: Vec<String>,
    // Состояние UI
    pub data_load_error: Option<String>,
    pub ui_mode: UIMode,
    pub normal_mode_size: Option<egui::Vec2>,
    pub show_about_window: bool,
    pub show_author_window: bool,
    pub show_settings_window: bool,
    // Настройки
    pub settings: AppSettings,
    // Системные менеджеры
    pub recognition_manager: Option<RecognitionManager>,
    pub hotkey_manager: HotkeyManager,
    hotkey_rx: mpsc::Receiver<HotkeyAction>,
    pub clipboard: arboard::Clipboard,
    // Флаг для предотвращения навигации Tab
    pub prevent_tab_navigation: bool,
    // Состояние вкладок
    pub active_tab: ActiveTab,
    // Контроль времени распознавания
    recognition_start_time: Option<std::time::Instant>,
    max_recognition_time: std::time::Duration,
    last_result_check: std::time::Instant,
}

#[derive(PartialEq, Debug, Clone, Copy)]
pub enum ActiveTab {
    Main,
    Settings,
    About,
    Author,
}

impl Default for ActiveTab {
    fn default() -> Self {
        ActiveTab::Main
    }
}

impl RivalsApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let (hotkey_tx, hotkey_rx) = mpsc::channel(8);
        let settings = settings_manager::load_settings().unwrap_or_default();
        
        // Логируем информацию о путях для отладки
        info!("Текущая рабочая директория: {:?}", std::env::current_dir());
        info!("Корень проекта: {:?}", crate::utils::get_project_root());
        
        // Загружаем данные с использованием правильных путей
        let data_result = data_loader::load_matchups_from_json("database/marvel_rivals_stats_20250810-055947.json");
        let roles_result = data_loader::load_roles_from_python_file("database/roles_and_groups.py");
            
        let mut app = Self {
            hotkey_rx,
            settings: settings.clone(),
            recognition_manager: None, // Не инициализируем сразу
            prevent_tab_navigation: false, // Изначально не блокируем Tab
            active_tab: ActiveTab::Main, // Основная вкладка по умолчанию
            recognition_start_time: None,
            max_recognition_time: std::time::Duration::from_secs(300), // 5 минут максимум
            last_result_check: std::time::Instant::now(),
            ..Self::default()
        };
        
        match (data_result, roles_result) {
            (Ok(data), Ok(roles)) => {
                // Выводим список героев из базы данных для отладки
                info!("=== СПИСОК ГЕРОЕВ ИЗ БАЗЫ ДАННЫХ ===");
                for _hero_name in data.keys() {
                    // info!("Герой из БД: {}", hero_name); // Закомментировано
                }
                info!("Всего героев в БД: {}", data.len());
                
                let mut hero_names: Vec<String> = data.keys().cloned().collect();
                hero_names.sort();
                app.hero_icons = image_loader::load_hero_icons(&hero_names, &cc.egui_ctx);
                app.all_heroes_data = data;
                app.hero_roles = roles;
                app.all_hero_names = hero_names;
                
                // Выводим финальный список имен героев
                info!("=== ФИНАЛЬНЫЙ СПИСОК ГЕРОЕВ ===");
                for (_i, _hero_name) in app.all_hero_names.iter().enumerate() {
                    // info!("Герой #{}: {}", i + 1, hero_name); // Закомментировано
                }
                
                match hotkey_manager::HotkeyManager::new(hotkey_tx, app.settings.hotkeys.clone()) {
                    Ok(hotkey_man) => {
                        app.hotkey_manager = hotkey_man;
                        info!("Менеджер хоткеев успешно инициализирован.");
                    }
                    Err(e) => {
                        let error_msg = format!("Ошибка инициализации хоткеев: {}", e);
                        error!("{}", error_msg);
                        // Не устанавливаем критическую ошибку, чтобы приложение могло работать без хоткеев
                        warn!("Приложение будет работать без поддержки горячих клавиш.");
                    }
                }
            }
            (Err(e), _) => {
                let error_msg = format!("Ошибка данных героев: {}", e);
                error!("{}", error_msg);
                app.data_load_error = Some(error_msg);
            }
            (_, Err(e)) => {
                let error_msg = format!("Ошибка ролей героев: {}", e);
                error!("{}", error_msg);
                app.data_load_error = Some(error_msg);
            }
        }
        app
    }
    
    pub fn update_ratings(&mut self) {
        if self.selected_enemies.is_empty() {
            self.calculated_rating.clear();
            self.optimal_team.clear();
            return;
        }
        let raw_scores = core_logic::calculate_hero_ratings(&self.selected_enemies, &self.all_heroes_data);
        let final_scores = core_logic::apply_context_to_scores(&raw_scores, &self.all_heroes_data);
        self.optimal_team = core_logic::select_optimal_team(&final_scores, &self.hero_roles);
        self.calculated_rating = final_scores;
    }
    
    fn handle_hotkey_action(&mut self, action: HotkeyAction) {
        match action {
            HotkeyAction::RecognizeHeroes => {
                info!("Хоткей 'Распознать героев' получен.");
                self.start_recognition();
            }
        }
    }
    
    pub fn start_recognition(&mut self) {
        if self.recognition_manager.is_none() {
            info!("Инициализация менеджера распознавания...");
            match RecognitionManager::new() {
                Ok(manager) => {
                    self.recognition_manager = Some(manager);
                    info!("Менеджер распознавания успешно инициализирован.");
                }
                Err(e) => {
                    let error_msg = format!("Ошибка распознавания: {}", e);
                    error!("{}", error_msg);
                    self.data_load_error = Some(error_msg);
                    return;
                }
            }
        }

        if let Some(ref mut manager) = self.recognition_manager {
            // Устанавливаем время начала распознавания
            self.recognition_start_time = Some(std::time::Instant::now());
            manager.start_recognition();
            info!("Запущено распознавание героев.");
        }
    }
    
    pub fn save_settings(&self) {
        if let Err(e) = settings_manager::save_settings(&self.settings) {
            let error_msg = format!("Не удалось сохранить настройки: {}", e);
            error!("{}", error_msg);
        }
    }
}
impl Default for RivalsApp {
    fn default() -> Self {
        let (hotkey_tx, hotkey_rx) = mpsc::channel(8);
        let settings = AppSettings::default();
        
        // Создаем менеджер хоткеев с обработкой возможной ошибки
        let hotkey_manager = match HotkeyManager::new(hotkey_tx, settings.hotkeys.clone()) {
            Ok(manager) => {
                info!("Менеджер хоткеев успешно инициализирован в Default.");
                manager
            }
            Err(e) => {
                warn!("Не удалось инициализировать менеджер хоткеев в Default: {}. Приложение будет работать без горячих клавиш.", e);
                // Создаем заглушку для менеджера хоткеев
                // В реальном приложении здесь нужно более сложное решение
                panic!("Критическая ошибка при инициализации менеджера хоткеев: {}", e);
            }
        };
        
        Self {
            all_heroes_data: Default::default(),
            hero_roles: Default::default(),
            all_hero_names: Default::default(),
            hero_icons: Default::default(),
            selected_enemies: Default::default(),
            calculated_rating: Default::default(),
            optimal_team: Default::default(),
            data_load_error: None,
            ui_mode: UIMode::Normal,
            normal_mode_size: None,
            show_about_window: false,
            show_author_window: false,
            show_settings_window: false,
            settings: settings.clone(),
            recognition_manager: None,
            hotkey_manager,
            hotkey_rx,
            clipboard: arboard::Clipboard::new().unwrap(),
            prevent_tab_navigation: false, // Изначально не блокируем Tab
            active_tab: ActiveTab::Main, // Основная вкладка по умолчанию
            recognition_start_time: None,
            max_recognition_time: std::time::Duration::from_secs(300), // 5 минут максимум
            last_result_check: std::time::Instant::now(),
        }
    }
}
impl eframe::App for RivalsApp {
    fn update(&mut self, ctx: &egui::Context, frame: &mut eframe::Frame) {
        // Проверяем и поглощаем событие Tab, чтобы предотвратить навигацию
        if self.prevent_tab_navigation {
            ctx.input_mut(|i| {
                // Проверяем, есть ли событие Tab и поглощаем его
                if i.key_pressed(egui::Key::Tab) {
                    i.consume_key(egui::Modifiers::NONE, egui::Key::Tab);
                }
                // Также проверяем Tab с модификаторами
                if i.key_pressed(egui::Key::Tab) && (i.modifiers.shift || i.modifiers.ctrl || i.modifiers.alt) {
                    i.consume_key(egui::Modifiers::SHIFT, egui::Key::Tab);
                    i.consume_key(egui::Modifiers::CTRL, egui::Key::Tab);
                    i.consume_key(egui::Modifiers::ALT, egui::Key::Tab);
                }
            });
        }
        
        if let Some(err) = &self.data_load_error {
            error!("Критическая ошибка в приложении: {}", err);
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.heading("Критическая ошибка");
                ui.colored_label(egui::Color32::RED, err);
                if ui.button("Скопировать ошибку").clicked() {
                    if let Err(e) = self.clipboard.set_text(err.clone()) {
                        error!("Не удалось скопировать ошибку в буфер обмена: {}", e);
                    }
                }
            });
            return;
        }
        
        if let Ok(action) = self.hotkey_rx.try_recv() {
            self.handle_hotkey_action(action);
        }
        
        // Проверяем результаты распознавания с контролем времени
        if let Some(ref mut manager) = self.recognition_manager {
            let now = std::time::Instant::now();

            // Проверяем таймаут распознавания
            if let Some(start_time) = self.recognition_start_time {
                if now.duration_since(start_time) > self.max_recognition_time {
                    warn!("Превышено максимальное время распознавания ({} сек), отменяем", self.max_recognition_time.as_secs());
                    self.recognition_manager = None;
                    self.recognition_start_time = None;
                    return;
                }
            }

            // Проверяем результаты не чаще чем раз в 100 мс
            if now.duration_since(self.last_result_check) > std::time::Duration::from_millis(100) {
                self.last_result_check = now;

                match manager.try_get_result() {
                    Ok(Some(heroes)) => {
                        info!("Получен результат распознавания: {:?}", heroes);
                        self.selected_enemies = heroes.into_iter().collect();
                        self.update_ratings();
                        self.recognition_start_time = None; // Сбрасываем таймер
                    }
                    Ok(None) => {
                        // Нет данных, ничего не делаем
                    }
                    Err(e) => {
                        let error_msg = format!("Ошибка распознавания: {}", e);
                        error!("{}", error_msg);
                        // Не устанавливаем data_load_error, так как это не критическая ошибка
                    }
                }
            }
        }
        
        // Устанавливаем прозрачность окна
        if self.settings.always_on_top {
            ctx.send_viewport_cmd(egui::ViewportCommand::WindowLevel(egui::WindowLevel::AlwaysOnTop));
        } else {
            ctx.send_viewport_cmd(egui::ViewportCommand::WindowLevel(egui::WindowLevel::Normal));
        }
        
        // Правильно устанавливаем прозрачность с помощью ViewportCommand::Transparent
        ctx.send_viewport_cmd(egui::ViewportCommand::Transparent(self.settings.window_opacity < 1.0));
        
        ui::top_panel::render(ctx, self, frame);
        
        // Отображаем содержимое вкладок
        ui::tab_content::render(ctx, self);
        
        // Отображаем диалоги только если они открыты (для обратной совместимости)
        ui::dialogs::render(ctx, self);
        ui::settings_window::render(ctx, self);
        
        // Отображаем основной контент только на основной вкладке
        if self.active_tab == ActiveTab::Main {
            match self.ui_mode {
                UIMode::Normal => {
                    let selection_changed = ui::right_panel::render(ctx, self);
                    ui::left_panel::render(ctx, self);
                    if selection_changed {
                        self.update_ratings();
                    }
                }
                UIMode::Minimal => {
                    ui::minimal_view::render(ctx, self);
                }
            }
        }
    }
}