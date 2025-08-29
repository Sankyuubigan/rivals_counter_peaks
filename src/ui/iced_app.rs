use crate::{
    core_logic, data_loader, hotkey_manager, image_loader,
    models::{AllHeroesData, HeroRoles},
    recognition::{RecognitionManager, RecognitionState},
    settings_manager::{self, AppSettings},
    window_manager,
};
use crate::keyboard_monitor;
use arboard::Clipboard;
use iced::{
    executor, theme,
    widget::{button, column, container, image, row, scrollable, text, Space},
    window, Alignment, Application, Command, Element, Length, Point, Size, Subscription, Theme, Renderer,
};
use log::{error, info};
use std::collections::HashMap;
use std::fs;
use tokio::sync::mpsc;
use std::path::PathBuf;

use super::settings_view;

// --- Сообщения, управляющие состоянием приложения ---
#[derive(Debug, Clone)]
pub enum Message {
    // Инициализация
    DataLoaded(Box<(Result<AllHeroesData, String>, Result<HeroRoles, String>, HashMap<String, image::Handle>)>),
    // Управление UI
    TabKeyPressed(bool),
    SwitchTab(ActiveTab),
    SwitchMode(UIMode),
    // Герои и распознавание
    ToggleHero(String),
    ClearSelection,
    StartRecognition,
    // Настройки
    ToggleAlwaysOnTop(bool),
    SaveSettings,
    ToggleSaveScreenshots(bool),
    ScreenshotPathChanged(String),
    BrowseScreenshotPath,
    ScreenshotPathSelected(Option<PathBuf>),
    // Системные тики и события
    Tick,
    WindowResized { width: u32, height: u32 },
    WindowMoved { x: i32, y: i32 },
    KeyboardEvent(keyboard_monitor::KeyboardEvent),
    // Сообщения для Win32 API управления окном
    InitWindowManager,
    SetWindowOverlay(bool),
    TimerTick,
}

// --- Режимы и вкладки UI (аналогично старой версии) ---
#[derive(PartialEq, Debug, Clone, Copy, Default)]
pub enum UIMode {
    #[default]
    Normal,
    Minimal,
}

#[derive(PartialEq, Debug, Clone, Copy, Default)]
pub enum ActiveTab {
    #[default]
    Main,
    Settings,
    About,
    Author,
}

// --- Структура для сохранения состояния окна ---
#[derive(Debug, Clone, Copy)]
struct WindowModeState {
    size: Size,
    position: Point,
}

// --- Основная структура приложения ---
pub struct IcedApp {
    // Данные
    all_heroes_data: AllHeroesData,
    hero_roles: HeroRoles,
    all_hero_names: Vec<String>,
    hero_icons: HashMap<String, image::Handle>,
    // Состояние
    selected_enemies: Vec<String>,
    calculated_rating: Vec<(String, f32)>,
    optimal_team: Vec<String>,
    // Состояние UI
    active_tab: ActiveTab,
    ui_mode: UIMode,
    data_load_error: Option<String>,
    tab_mode_active: bool,
    pre_tab_mode_state: Option<WindowModeState>,
    restoring_from_tab: bool, // Флаг для предотвращения перезаписи состояния окна
    // Настройки
    pub settings: AppSettings,
    // Системные компоненты
    recognition_manager: Option<RecognitionManager>,
    keyboard_rx: mpsc::Receiver<keyboard_monitor::KeyboardEvent>,
    _clipboard: Clipboard,
    // Window manager для overlay функциональности
    window_manager_initialized: bool,
    init_timer: u8, // счетчик тиков для отсроченной инициализации
}

// --- Реализация трейта Application для Iced ---
impl Application for IcedApp {
    type Executor = executor::Default;
    type Message = Message;
    type Theme = Theme;
    type Flags = ();

    fn new(_flags: ()) -> (Self, Command<Message>) {
        let (keyboard_tx, keyboard_rx) = mpsc::channel(8);
        let keyboard_monitor = keyboard_monitor::KeyboardMonitor::new(keyboard_tx);

        keyboard_monitor.start();

        let settings = settings_manager::load_settings().unwrap_or_default();
        
        let app = Self {
            all_heroes_data: HashMap::new(),
            hero_roles: HeroRoles::default(),
            all_hero_names: Vec::new(),
            hero_icons: HashMap::new(),
            selected_enemies: Vec::new(),
            calculated_rating: Vec::new(),
            optimal_team: Vec::new(),
            active_tab: ActiveTab::default(),
            ui_mode: UIMode::default(),
            data_load_error: None,
            tab_mode_active: false,
            pre_tab_mode_state: None,
            restoring_from_tab: false,
            settings,
            keyboard_rx,
            recognition_manager: None,
            _clipboard: Clipboard::new().expect("Failed to initialize clipboard"),
            window_manager_initialized: false,
            init_timer: 0,
        };

        (app, Command::perform(load_data_async(), |result| Message::DataLoaded(Box::new(result))))
    }

    fn title(&self) -> String {
        String::from("Rivals Counter Peaks")
    }

    fn update(&mut self, message: Message) -> Command<Message> {
        match message {
            Message::DataLoaded(results) => {
                let (data_result, roles_result, icons) = *results;
                self.hero_icons = icons;
                match (data_result, roles_result) {
                    (Ok(data), Ok(roles)) => {
                        let mut hero_names: Vec<String> = data.keys().cloned().collect();
                        hero_names.sort();
                        self.all_heroes_data = data;
                        self.hero_roles = roles;
                        self.all_hero_names = hero_names;
                    }
                    (Err(e), _) | (_, Err(e)) => self.data_load_error = Some(e),
                }
            }
            Message::TabKeyPressed(pressed) => return self.handle_tab_mode(pressed),
            Message::SwitchTab(tab) => self.active_tab = tab,
            Message::SwitchMode(mode) => return self.handle_mode_switch(mode),
            Message::ToggleHero(hero_name) => {
                if let Some(pos) = self.selected_enemies.iter().position(|h| h == &hero_name) {
                    self.selected_enemies.remove(pos);
                } else if self.selected_enemies.len() < 6 {
                    self.selected_enemies.push(hero_name);
                }
                self.update_ratings();
            }
            Message::ClearSelection => {
                self.selected_enemies.clear();
                self.update_ratings();
            }
            Message::StartRecognition => {
                self.start_recognition();
                return Command::none();
            }
            Message::ToggleAlwaysOnTop(is_on) => {
                self.settings.always_on_top = is_on;
                #[cfg(target_os = "windows")]
                if self.window_manager_initialized && !self.tab_mode_active {
                    let _ = self.update(Message::SetWindowOverlay(is_on));
                }
            },
            Message::SaveSettings => self.save_settings(),
            Message::ToggleSaveScreenshots(checked) => self.settings.save_failed_screenshots = checked,
            Message::ScreenshotPathChanged(new_path) => self.settings.screenshot_path = new_path,
            Message::BrowseScreenshotPath => {
                return Command::perform(async {
                    rfd::AsyncFileDialog::new().pick_folder().await
                }, |handle| {
                    Message::ScreenshotPathSelected(handle.map(|h| h.path().to_path_buf()))
                });
            }
            Message::ScreenshotPathSelected(path) => {
                if let Some(p) = path {
                    self.settings.screenshot_path = p.to_string_lossy().to_string();
                }
            }
            Message::Tick => self.check_for_events(),
            Message::WindowResized { width, height } => {
                if !self.tab_mode_active {
                    if self.restoring_from_tab {
                        self.restoring_from_tab = false;
                    } else {
                        let size = Size::new(width as f32, height as f32);
                        if let Some(state) = &mut self.pre_tab_mode_state {
                            state.size = size;
                        } else {
                            self.pre_tab_mode_state = Some(WindowModeState { size, position: Point::new(100.0, 100.0) });
                        }
                    }
                }
            }
            Message::WindowMoved { x, y } => {
                if !self.tab_mode_active {
                    let position = Point::new(x as f32, y as f32);
                    if let Some(state) = &mut self.pre_tab_mode_state {
                        state.position = position;
                    }
                }
            }
            Message::KeyboardEvent(event) => return self.handle_keyboard_event(event),
            Message::InitWindowManager => {
                self.init_window_manager();
                return Command::none();
            }
            Message::SetWindowOverlay(always_on_top) => {
                self.set_window_overlay(always_on_top);
                return Command::none();
            }
            Message::TimerTick => {
                self.handle_timer_tick();
                return Command::none();
            }
        }
        Command::none()
    }

    fn view(&self) -> Element<'_, Message> {
        let content: Element<'_, Message> = if let Some(err) = &self.data_load_error {
             container(text(err).size(20))
                .width(Length::Fill)
                .height(Length::Fill)
                .center_x()
                .center_y()
                .into()
        } else {
            let top_panel = self.view_top_panel();
            let main_content = match self.active_tab {
                ActiveTab::Main => {
                    if self.tab_mode_active {
                        self.view_main_minimal_mode()
                    } else {
                        match self.ui_mode {
                            UIMode::Normal => self.view_main_normal_mode(),
                            UIMode::Minimal => self.view_main_minimal_mode(),
                        }
                    }
                },
                ActiveTab::Settings => settings_view::view_settings_tab(self),
                _ => self.view_placeholder_tab(),
            };
            column![top_panel, main_content].spacing(10).padding(15).into()
        };

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .style(theme::Container::Box)
            .into()
    }

    fn subscription(&self) -> Subscription<Message> {
        let tick_sub = iced::time::every(std::time::Duration::from_millis(50)).map(|_| Message::Tick);
        let init_timer_sub = iced::time::every(std::time::Duration::from_millis(100)).map(|_| Message::TimerTick);

        let window_events = iced::event::listen_with(|event, _| match event {
            iced::Event::Window(_, window::Event::Resized { width, height }) => Some(Message::WindowResized { width, height }),
            iced::Event::Window(_, window::Event::Moved { x, y }) => Some(Message::WindowMoved { x, y }),
            _ => None,
        });

        Subscription::batch(vec![tick_sub, init_timer_sub, window_events])
    }

    fn theme(&self) -> Self::Theme {
        Theme::Dark
    }
}

// --- Вспомогательные методы и логика ---
impl IcedApp {
    fn update_ratings(&mut self) {
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

    fn start_recognition(&mut self) {
        if self.recognition_manager.is_none() {
            match RecognitionManager::new() {
                Ok(manager) => self.recognition_manager = Some(manager),
                Err(e) => {
                    self.data_load_error = Some(format!("Ошибка инициализации распознавания: {}", e));
                    return;
                }
            }
        }
        if let Some(manager) = &mut self.recognition_manager {
            manager.start_recognition();
        }
    }

    fn check_for_events(&mut self) {
        if let Some(manager) = &mut self.recognition_manager {
            if let Ok(Some(heroes)) = manager.try_get_result() {
                info!("Распознано: {:?}", heroes);
                if heroes.len() < 6 && self.settings.save_failed_screenshots {
                    self.save_debug_screenshot();
                }
                self.selected_enemies = heroes;
                self.update_ratings();
            }
        }
        
        if let Ok(keyboard_event) = self.keyboard_rx.try_recv() {
            let _ = self.update(Message::KeyboardEvent(keyboard_event));
        }
    }

    fn save_debug_screenshot(&self) {
        let path_str = &self.settings.screenshot_path;
        if path_str.is_empty() { return; }
        let path = std::path::PathBuf::from(path_str);
        if let Err(e) = fs::create_dir_all(&path) {
            error!("Не удалось создать директорию для скриншотов '{}': {}", path.display(), e);
            return;
        }
        if let Ok(monitors) = xcap::Monitor::all() {
            if let Some(monitor) = monitors.first() {
                if let Ok(image) = monitor.capture_image() {
                    let timestamp = chrono::Local::now().format("%Y-%m-%d_%H-%M-%S").to_string();
                    let filename = path.join(format!("recognition_failed_{}.png", timestamp));
                    if let Err(e) = image.save(&filename) {
                        error!("Не удалось сохранить скриншот в {:?}: {}", filename, e);
                    } else {
                        info!("Скриншот сохранен в {:?}", filename);
                    }
                }
            }
        }
    }

    fn save_settings(&mut self) {
        if let Err(e) = settings_manager::save_settings(&self.settings) {
            error!("Не удалось сохранить настройки: {}", e);
        }
        info!("Настройки сохранены.");

        #[cfg(target_os = "windows")]
        if self.window_manager_initialized && !self.tab_mode_active {
            let _ = self.update(Message::SetWindowOverlay(self.settings.always_on_top));
        }
    }

    fn handle_mode_switch(&mut self, mode: UIMode) -> Command<Message> {
        self.ui_mode = mode;
        match mode {
            UIMode::Normal => {
                let size = self.pre_tab_mode_state.map_or(Size::new(1024.0, 768.0), |s| s.size);
                window::resize(window::Id::MAIN, size)
            }
            UIMode::Minimal => {
                window::resize(window::Id::MAIN, Size::new(1200.0, 120.0))
            }
        }
    }

    fn handle_tab_mode(&mut self, pressed: bool) -> Command<Message> {
        if pressed && !self.tab_mode_active {
            self.tab_mode_active = true;
            let (screen_w, _) = xcap::Monitor::all().ok()
                .and_then(|m| m.first().map(|m| (m.width() as f32, m.height() as f32)))
                .unwrap_or((1920.0, 1080.0));
            let tab_width = screen_w * 0.4;
            let tab_height = 120.0;

            #[cfg(target_os = "windows")]
            if self.window_manager_initialized {
                if let Err(e) = window_manager::move_resize_window(0, 0, tab_width as i32, tab_height as i32) {
                    error!("Failed to move/resize window with Win32 API: {}", e);
                }
                let _ = self.update(Message::SetWindowOverlay(true));
            }

            Command::none()

        } else if !pressed && self.tab_mode_active {
            self.tab_mode_active = false;
            self.restoring_from_tab = true; // Устанавливаем флаг перед изменением размера
            let restore_state = self.pre_tab_mode_state.unwrap_or(WindowModeState {
                size: Size::new(1024.0, 768.0),
                position: Point::new(100.0, 100.0),
            });

            #[cfg(target_os = "windows")]
            if self.window_manager_initialized {
                if let Err(e) = self.set_window_overlay_directly(self.settings.always_on_top) {
                    error!("Failed to restore window overlay status: {}", e);
                }
                if let Err(e) = window_manager::move_resize_window(
                    restore_state.position.x as i32,
                    restore_state.position.y as i32,
                    restore_state.size.width as i32,
                    restore_state.size.height as i32
                ) {
                    error!("Failed to restore window with Win32 API: {}", e);
                }
            }
            Command::none()
        } else {
            Command::none()
        }
    }

    fn handle_keyboard_event(&mut self, event: keyboard_monitor::KeyboardEvent) -> Command<Message> {
        match event {
            keyboard_monitor::KeyboardEvent::TabPressed => {
                log::debug!("TAB key pressed via global monitor");
                self.handle_tab_mode(true)
            }
            keyboard_monitor::KeyboardEvent::TabReleased => {
                log::debug!("TAB key released via global monitor");
                self.handle_tab_mode(false)
            }
            keyboard_monitor::KeyboardEvent::Recognize => {
                log::info!("Recognize hotkey (TAB+0) pressed");
                self.start_recognition();
                Command::none()
            }
        }
    }

    #[cfg(target_os = "windows")]
    fn init_window_manager(&mut self) {
        let window_titles = ["Rivals Counter Peaks", ""];
        for title in &window_titles {
            if let Ok(()) = window_manager::init_window_manager(title) {
                self.window_manager_initialized = true;
                log::info!("Window manager initialized successfully with title: '{}'", title);
                break;
            } else {
                log::debug!("Failed to find window with title: '{}', trying next...", title);
            }
        }
        if !self.window_manager_initialized {
            log::warn!("Could not initialize window manager - overlay functionality may not work");
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn init_window_manager(&mut self) {
        log::warn!("Window overlay functionality is only available on Windows");
        self.window_manager_initialized = false;
    }

    #[cfg(target_os = "windows")]
    fn set_window_overlay(&mut self, always_on_top: bool) {
        if !self.window_manager_initialized { return; }
        let result = if always_on_top {
            window_manager::activate_overlay_mode()
        } else {
            window_manager::deactivate_overlay_mode()
        };
        if let Err(e) = result {
            log::error!("Failed to set window overlay: {}", e);
        }
    }

    #[cfg(target_os = "windows")]
    fn set_window_overlay_directly(&mut self, always_on_top: bool) -> Result<(), String> {
        if !self.window_manager_initialized { return Ok(()); }
        if always_on_top {
            window_manager::activate_overlay_mode()
        } else {
            window_manager::deactivate_overlay_mode()
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn set_window_overlay(&mut self, _always_on_top: bool) {}

    fn handle_timer_tick(&mut self) {
        self.init_timer += 1;
        if self.init_timer == 30 && !self.window_manager_initialized {
            log::debug!("Timer triggered window manager initialization");
            let _ = self.update(Message::InitWindowManager);
        }
    }

    fn view_top_panel(&self) -> Element<'_, Message> {
        if self.tab_mode_active {
            return Space::new(Length::Shrink, Length::Shrink).into();
        }

        let mode_buttons = row![
            button("Обычный").style(get_button_style(self.ui_mode == UIMode::Normal)).on_press(Message::SwitchMode(UIMode::Normal)),
            button("Минимальный").style(get_button_style(self.ui_mode == UIMode::Minimal)).on_press(Message::SwitchMode(UIMode::Minimal)),
        ].spacing(5);

        let tab_buttons: iced::widget::Row<'_, Message, Theme, Renderer> = row![
            button("Основная").style(get_button_style(self.active_tab == ActiveTab::Main)).on_press(Message::SwitchTab(ActiveTab::Main)),
            button("Настройки").style(get_button_style(self.active_tab == ActiveTab::Settings)).on_press(Message::SwitchTab(ActiveTab::Settings)),
        ].spacing(5);

        let tab_content: Element<'_, Message> = if self.ui_mode == UIMode::Normal {
            tab_buttons.into()
        } else {
            Space::new(Length::Shrink, Length::Shrink).into()
        };

        column![
            row![mode_buttons, Space::with_width(Length::Fill)].spacing(20),
            tab_content
        ].spacing(5).into()
    }

    fn view_main_normal_mode(&self) -> Element<'_, Message> {
        row![
            container(self.view_left_panel()).width(Length::FillPortion(2)).padding(10),
            container(self.view_right_panel()).width(Length::FillPortion(1)).padding(10)
        ].spacing(10).into()
    }

    fn view_left_panel(&self) -> Element<'_, Message> {
        let content = if self.selected_enemies.is_empty() {
            column![text("Выберите врагов на панели справа.")]
        } else {
            let optimal_team_icons = self.optimal_team.iter().fold(row![].spacing(5), |r, name| {
                if let Some(handle) = self.hero_icons.get(name) { r.push(image(handle.clone()).width(Length::Fixed(48.0))) }
                else { r.push(text(name).size(12)) }
            });
            let ratings_list = scrollable(
                column(self.calculated_rating.iter().map(|(h, s)| text(format!("{:<20}: {:.2}", h, s)).into()).collect::<Vec<_>>()).spacing(5)
            );
            column![
                text(format!("Против: {}", self.selected_enemies.join(", "))),
                text("Оптимальная команда:").size(18),
                optimal_team_icons,
                text("Полный рейтинг героев:").size(18),
                ratings_list
            ].spacing(10)
        };
        column![text("Рейтинг контрпиков").size(24), content].spacing(15).into()
    }

    fn view_right_panel(&self) -> Element<'_, Message> {
        let (rec_text, is_rec) = match self.recognition_manager.as_ref().map(|m| m.get_state()) {
            Some(RecognitionState::Recognizing) => ("Распознавание...", true),
            _ => ("Распознать героев", false),
        };
        let rec_button = button(rec_text).on_press_maybe(if is_rec { None } else { Some(Message::StartRecognition) });

        let hero_grid = scrollable(self.all_hero_names.chunks(5).fold(column![].spacing(5), |cols, chunk| {
            cols.push(row(chunk.iter().map(|hero| {
                let is_selected = self.selected_enemies.contains(hero);
                let content: Element<'_, Message> = if let Some(h) = self.hero_icons.get(hero) {
                    image(h.clone()).width(Length::Fixed(48.0)).height(Length::Fixed(48.0)).into()
                } else { text(hero).size(12).into() };
                button(container(content).center_x().center_y())
                    .style(get_button_style(is_selected))
                    .on_press(Message::ToggleHero(hero.clone())).width(Length::Fill).height(Length::Fixed(56.0)).padding(4).into()
            }).collect::<Vec<_>>()).spacing(5))
        }));

        column![
            text("Вражеская команда").size(24),
            row![rec_button, button("Очистить").on_press(Message::ClearSelection)].spacing(10),
            Space::with_height(10),
            hero_grid
        ].spacing(10).into()
    }

    fn view_main_minimal_mode(&self) -> Element<'_, Message> {
        let optimal_team = row(self.optimal_team.iter().map(|name| {
            if let Some(h) = self.hero_icons.get(name) { image(h.clone()).width(Length::Fixed(32.0)).into() }
            else { text(name).size(10).into() }
        }).collect::<Vec<_>>()).spacing(4);
        let enemies = row(self.selected_enemies.iter().map(|name| {
            if let Some(h) = self.hero_icons.get(name) { image(h.clone()).width(Length::Fixed(32.0)).into() }
            else { text(name).size(10).into() }
        }).collect::<Vec<_>>()).spacing(4);
        let (rec_text, is_rec) = match self.recognition_manager.as_ref().map(|m| m.get_state()) {
            Some(RecognitionState::Recognizing) => ("...", true),
            _ => ("Распознать", false),
        };
        let rec_button = button(rec_text).padding(5).on_press_maybe(if is_rec { None } else { Some(Message::StartRecognition) });

        container(row![
            text("Рекомендации:"), optimal_team, Space::with_width(Length::Fixed(20.0)),
            text("Враги:"), enemies, Space::with_width(Length::Fill), rec_button,
        ].align_items(Alignment::Center).spacing(10)).width(Length::Fill).center_y().padding(10).into()
    }
    
    fn view_placeholder_tab(&self) -> Element<'_, Message> {
        let name = match self.active_tab {
            ActiveTab::About => "О программе", ActiveTab::Author => "Об авторе", _ => "Неизвестно"
        };
        container(text(format!("Здесь будет содержимое вкладки '{}'", name)))
            .width(Length::Fill).height(Length::Fill).center_x().center_y().into()
    }
}

// --- Вспомогательные функции ---
pub fn get_button_style(is_active: bool) -> theme::Button {
    if is_active { theme::Button::Primary } else { theme::Button::Secondary }
}

async fn load_data_async() -> (Result<AllHeroesData, String>, Result<HeroRoles, String>, HashMap<String, image::Handle>) {
    let data_res = data_loader::load_matchups_from_json("database/marvel_rivals_stats_20250810-055947.json")
        .map_err(|e| format!("Ошибка загрузки данных героев: {}", e));
    let roles_res = data_loader::load_roles_from_python_file("database/roles_and_groups.py")
        .map_err(|e| format!("Ошибка загрузки ролей: {}", e));
    let hero_names = if let Ok(data) = &data_res { data.keys().cloned().collect() } else { Vec::new() };
    let icons = image_loader::load_hero_icons(&hero_names);
    (data_res, roles_res, icons)
}