use crate::{
    core_logic, data_loader, hotkey_manager, image_loader,
    models::{AllHeroesData, HeroRoles},
    recognition::{RecognitionManager, RecognitionState},
    settings_manager::{self, AppSettings},
};
use arboard::Clipboard;
use iced::{
    executor, keyboard, theme,
    widget::{button, checkbox, column, container, image, row, scrollable, slider, text, Space},
    window, Alignment, Application, Command, Element, Length, Point, Size, Subscription, Theme,
};
use log::{error, info};
use std::collections::HashMap;
use std::fs;
use tokio::sync::mpsc;

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
    OpacityChanged(f32),
    SaveSettings,
    // Системные тики и события
    Tick,
    WindowResized { width: u32, height: u32 },
    WindowMoved { x: i32, y: i32 },
    HotkeyAction(hotkey_manager::HotkeyAction),
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
    // Настройки
    settings: AppSettings,
    // Системные компоненты
    recognition_manager: Option<RecognitionManager>,
    hotkey_rx: mpsc::Receiver<hotkey_manager::HotkeyAction>,
    _clipboard: Clipboard,
}

// --- Реализация трейта Application для Iced ---
impl Application for IcedApp {
    type Executor = executor::Default;
    type Message = Message;
    type Theme = Theme;
    type Flags = ();

    fn new(_flags: ()) -> (Self, Command<Message>) {
        let (hotkey_tx, hotkey_rx) = mpsc::channel(8);
        let settings = settings_manager::load_settings().unwrap_or_default();

        if let Err(e) = hotkey_manager::initialize(hotkey_tx, settings.hotkeys.clone()) {
            error!("Не удалось инициализировать менеджер горячих клавиш: {}", e);
        }

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
            settings,
            hotkey_rx,
            recognition_manager: None,
            _clipboard: Clipboard::new().expect("Failed to initialize clipboard"),
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
            Message::StartRecognition => self.start_recognition(),
            Message::ToggleAlwaysOnTop(is_on) => self.settings.always_on_top = is_on,
            Message::OpacityChanged(opacity) => self.settings.window_opacity = opacity,
            Message::SaveSettings => self.save_settings(),
            Message::Tick => self.check_for_events(),
            Message::WindowResized { width, height } => {
                if !self.tab_mode_active {
                    let size = Size::new(width as f32, height as f32);
                    if let Some(state) = &mut self.pre_tab_mode_state {
                        state.size = size;
                    } else {
                        self.pre_tab_mode_state = Some(WindowModeState { size, position: Point::new(100.0, 100.0) });
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
            Message::HotkeyAction(action) => {
                match action {
                    hotkey_manager::HotkeyAction::RecognizeHeroes => self.start_recognition(),
                    hotkey_manager::HotkeyAction::ToggleTabMode(_) => {
                        return self.handle_tab_mode_toggle();
                    }
                }
            }
        }
        Command::none()
    }

    fn view(&self) -> Element<'_, Message> {
        if let Some(err) = &self.data_load_error {
            return container(text(err).size(20)).width(Length::Fill).height(Length::Fill).center_x().center_y().into();
        }

        let top_panel = self.view_top_panel();
        let content = match self.active_tab {
            ActiveTab::Main => {
                if self.tab_mode_active {
                    // В таб-режиме всегда показываем минимальный режим
                    self.view_main_minimal_mode()
                } else {
                    // Обычная логика переключения режимов
                    match self.ui_mode {
                        UIMode::Normal => self.view_main_normal_mode(),
                        UIMode::Minimal => self.view_main_minimal_mode(),
                    }
                }
            },
            _ => self.view_placeholder_tab(),
        };

        column![top_panel, content].spacing(10).padding(15).into()
    }

    fn subscription(&self) -> Subscription<Message> {
        let keyboard_sub = keyboard::on_key_press(|key, _mods| match key {
            keyboard::Key::Named(keyboard::key::Named::Tab) => Some(Message::TabKeyPressed(true)),
            _ => None,
        });

        let keyrelease_sub = keyboard::on_key_release(|key, _mods| match key {
            keyboard::Key::Named(keyboard::key::Named::Tab) => Some(Message::TabKeyPressed(false)),
            _ => None,
        });

        let tick_sub = iced::time::every(std::time::Duration::from_millis(50)).map(|_| Message::Tick);
        
        let window_events = iced::event::listen_with(|event, _| match event {
            iced::Event::Window(_, window::Event::Resized { width, height }) => Some(Message::WindowResized { width, height }),
            iced::Event::Window(_, window::Event::Moved { x, y }) => Some(Message::WindowMoved { x, y }),
            _ => None,
        });

        Subscription::batch(vec![keyboard_sub, keyrelease_sub, tick_sub, window_events])
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
                if heroes.len() < 6 {
                    self.save_debug_screenshot();
                }
                self.selected_enemies = heroes;
                self.update_ratings();
            }
        }
        if let Ok(action) = self.hotkey_rx.try_recv() {
            let _ = self.update(Message::HotkeyAction(action));
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

    fn handle_tab_mode_toggle(&mut self) -> Command<Message> {
        if !self.tab_mode_active {
            // Включаем таб-режим
            self.tab_mode_active = true;
            let (screen_w, _) = xcap::Monitor::all().ok()
                .and_then(|m| m.first().map(|m| (m.width() as f32, m.height() as f32)))
                .unwrap_or((1920.0, 1080.0));
            let tab_width = screen_w * 0.8; // Немного шире для лучшей видимости
            let tab_height = 120.0;
            Command::batch(vec![
                window::resize(window::Id::MAIN, Size::new(tab_width, tab_height)),
                window::move_to(window::Id::MAIN, Point::new(0.0, 0.0)),
                window::change_level(window::Id::MAIN, window::Level::AlwaysOnTop),
            ])
        } else {
            // Выключаем таб-режим
            self.tab_mode_active = false;
            let restore_state = self.pre_tab_mode_state.unwrap_or(WindowModeState {
                size: Size::new(1024.0, 768.0),
                position: Point::new(100.0, 100.0),
            });
            let level = if self.settings.always_on_top { window::Level::AlwaysOnTop } else { window::Level::Normal };
            Command::batch(vec![
                window::resize(window::Id::MAIN, restore_state.size),
                window::move_to(window::Id::MAIN, restore_state.position),
                window::change_level(window::Id::MAIN, level),
            ])
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
            Command::batch(vec![
                window::resize(window::Id::MAIN, Size::new(tab_width, tab_height)),
                window::move_to(window::Id::MAIN, Point::new(0.0, 0.0)),
                window::change_level(window::Id::MAIN, window::Level::AlwaysOnTop),
            ])
        } else if !pressed && self.tab_mode_active {
            self.tab_mode_active = false;
            let restore_state = self.pre_tab_mode_state.unwrap_or(WindowModeState {
                size: Size::new(1024.0, 768.0),
                position: Point::new(100.0, 100.0),
            });
            let level = if self.settings.always_on_top { window::Level::AlwaysOnTop } else { window::Level::Normal };
            Command::batch(vec![
                window::resize(window::Id::MAIN, restore_state.size),
                window::move_to(window::Id::MAIN, restore_state.position),
                window::change_level(window::Id::MAIN, level),
            ])
        } else {
            Command::none()
        }
    }

    // --- Методы отрисовки ---
    fn view_top_panel(&self) -> Element<'_, Message> {
        if self.tab_mode_active {
            // В таб-режиме скрываем все кнопки управления, включая настройки прозрачности
            return column![
                Space::with_height(Length::Fixed(5.0)),
                Space::with_height(Length::Fixed(5.0))
            ].into()
        }

        let mode_buttons = row![
            button("Обычный").style(get_button_style(self.ui_mode == UIMode::Normal)).on_press(Message::SwitchMode(UIMode::Normal)),
            button("Минимальный").style(get_button_style(self.ui_mode == UIMode::Minimal)).on_press(Message::SwitchMode(UIMode::Minimal)),
        ].spacing(5);

        let tab_buttons: iced::widget::Row<'_, Message, Theme, iced::Renderer> = row![
            button("Основная").style(get_button_style(self.active_tab == ActiveTab::Main)).on_press(Message::SwitchTab(ActiveTab::Main)),
            button("Настройки").style(get_button_style(self.active_tab == ActiveTab::Settings)).on_press(Message::SwitchTab(ActiveTab::Settings)),
            button("О программе").style(get_button_style(self.active_tab == ActiveTab::About)).on_press(Message::SwitchTab(ActiveTab::About)),
            button("Об авторе").style(get_button_style(self.active_tab == ActiveTab::Author)).on_press(Message::SwitchTab(ActiveTab::Author)),
        ].spacing(5);

        let settings_controls = row![
            checkbox("Поверх всех окон", self.settings.always_on_top).on_toggle(Message::ToggleAlwaysOnTop),
            text("Прозрачность:"),
            slider(0.1..=1.0, self.settings.window_opacity, Message::OpacityChanged).step(0.01).width(Length::Fixed(100.0)),
        ].spacing(10).align_items(Alignment::Center);

        column![
            row![mode_buttons, Space::with_width(Length::Fill), settings_controls].spacing(20),
            {
                let tab_content: Element<'_, Message> = if self.ui_mode == UIMode::Normal {
                    tab_buttons.into()
                } else {
                    Space::new(Length::Fixed(0.0), Length::Fixed(0.0)).into()
                };
                tab_content
            }
        ].spacing(5).into()
    }

    fn view_main_normal_mode(&self) -> Element<'_, Message> {
        row![
            container(self.view_left_panel()).width(Length::FillPortion(2)).padding(10).style(theme::Container::Box),
            container(self.view_right_panel()).width(Length::FillPortion(1)).padding(10).style(theme::Container::Box)
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
        ].align_items(Alignment::Center).spacing(10)).width(Length::Fill).center_y().padding(10).style(theme::Container::Box).into()
    }
    
    fn view_placeholder_tab(&self) -> Element<'_, Message> {
        let name = match self.active_tab {
            ActiveTab::Settings => "Настройки", ActiveTab::About => "О программе", ActiveTab::Author => "Об авторе", _ => "Неизвестно"
        };
        container(text(format!("Здесь будет содержимое вкладки '{}'", name)))
            .width(Length::Fill).height(Length::Fill).center_x().center_y().into()
    }
}

// --- Вспомогательные функции ---
fn get_button_style(is_active: bool) -> theme::Button {
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