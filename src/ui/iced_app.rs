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
    DataLoaded(
        Box<(
            Result<AllHeroesData, String>,
            Result<HeroRoles, String>,
            HashMap<String, image::Handle>,
        )>,
    ),
    // Управление UI
    TabKeyPressed(bool),
    SwitchTab(ActiveTab),
    // Герои и распознавание
    ToggleHero(String),
    ClearSelection,
    StartRecognition,
    // Настройки
    ToggleAlwaysOnTop(bool),
    OpacityChanged(f32),
    SaveSettings,
    // Системные тики
    Tick,
    // События окна для сохранения его состояния
    WindowResized { width: u32, height: u32 },
    WindowMoved { x: i32, y: i32 },
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
    data_load_error: Option<String>,
    // Режим Таба
    tab_mode_active: bool,
    pre_tab_mode_state: Option<WindowModeState>,
    // Настройки
    settings: AppSettings,
    // Системные компоненты
    recognition_manager: Option<RecognitionManager>,
    hotkey_rx: mpsc::Receiver<hotkey_manager::HotkeyAction>,
    _clipboard: Clipboard,
}

#[derive(PartialEq, Debug, Clone, Copy, Default)]
pub enum ActiveTab {
    #[default]
    Main,
    Settings,
}

#[derive(Debug, Clone)]
struct WindowModeState {
    size: Size,
    position: Point,
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

        // РЕШЕНИЕ ПРОБЛЕМЫ С ПАНИКОЙ: менеджер инициализируется здесь один раз
        // и запускается в отдельном потоке, не привязанном к жизненному циклу IcedApp.
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
            data_load_error: None,
            tab_mode_active: false,
            pre_tab_mode_state: None,
            settings,
            hotkey_rx,
            recognition_manager: None,
            _clipboard: Clipboard::new().expect("Failed to initialize clipboard"),
        };

        (
            app,
            Command::perform(load_data_async(), |result| {
                Message::DataLoaded(Box::new(result))
            }),
        )
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
            Message::Tick => {
                self.check_recognition_results();
                self.check_hotkey_events();
            }
            Message::WindowResized { width, height } => {
                 if !self.tab_mode_active {
                    if let Some(state) = &mut self.pre_tab_mode_state {
                        state.size = Size::new(width as f32, height as f32);
                    } else {
                        self.pre_tab_mode_state = Some(WindowModeState {
                            size: Size::new(width as f32, height as f32),
                            position: Point::new(100.0, 100.0),
                        });
                    }
                }
            }
            Message::WindowMoved { x, y } => {
                if !self.tab_mode_active {
                     if let Some(state) = &mut self.pre_tab_mode_state {
                        state.position = Point::new(x as f32, y as f32);
                    }
                }
            }
        }
        Command::none()
    }

    fn view(&self) -> Element<'_, Message> {
        if let Some(err) = &self.data_load_error {
            return container(text(err).size(20))
                .width(Length::Fill)
                .height(Length::Fill)
                .center_x()
                .center_y()
                .into();
        }

        let top_panel = row![
            button("Основная").on_press(Message::SwitchTab(ActiveTab::Main)),
            button("Настройки").on_press(Message::SwitchTab(ActiveTab::Settings)),
        ]
        .spacing(10);

        let content = match self.active_tab {
            ActiveTab::Main => self.view_main_tab(),
            ActiveTab::Settings => self.view_settings_tab(),
        };

        column![top_panel, content]
            .spacing(10)
            .padding(15)
            .into()
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

        let tick_sub =
            iced::time::every(std::time::Duration::from_millis(50)).map(|_| Message::Tick);
        
        let window_events = iced::event::listen_with(|event, _| match event {
            iced::Event::Window(_, window::Event::Resized { width, height }) => Some(Message::WindowResized { width, height }),
            iced::Event::Window(_, window::Event::Moved { x, y }) => Some(Message::WindowMoved { x, y }),
            _ => None
        });

        Subscription::batch(vec![keyboard_sub, keyrelease_sub, tick_sub, window_events])
    }

    fn theme(&self) -> Self::Theme {
        Theme::Dark
    }
}

// --- Вспомогательные методы для IcedApp ---
impl IcedApp {
    fn update_ratings(&mut self) {
        if self.selected_enemies.is_empty() {
            self.calculated_rating.clear();
            self.optimal_team.clear();
            return;
        }
        let raw_scores =
            core_logic::calculate_hero_ratings(&self.selected_enemies, &self.all_heroes_data);
        let final_scores =
            core_logic::apply_context_to_scores(&raw_scores, &self.all_heroes_data);
        self.optimal_team = core_logic::select_optimal_team(&final_scores, &self.hero_roles);
        self.calculated_rating = final_scores;
    }

    fn start_recognition(&mut self) {
        if self.recognition_manager.is_none() {
            match RecognitionManager::new() {
                Ok(manager) => self.recognition_manager = Some(manager),
                Err(e) => {
                    self.data_load_error =
                        Some(format!("Ошибка инициализации распознавания: {}", e));
                    return;
                }
            }
        }
        if let Some(manager) = &mut self.recognition_manager {
            manager.start_recognition();
        }
    }

    fn check_recognition_results(&mut self) {
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
    }

    fn check_hotkey_events(&mut self) {
        if let Ok(action) = self.hotkey_rx.try_recv() {
            match action {
                hotkey_manager::HotkeyAction::RecognizeHeroes => self.start_recognition(),
            }
        }
    }

    fn save_debug_screenshot(&self) {
        let path_str = &self.settings.screenshot_path;
        if path_str.is_empty() {
            return;
        }
        let path = std::path::PathBuf::from(path_str);
        if let Err(e) = fs::create_dir_all(&path) {
            error!(
                "Не удалось создать директорию для скриншотов '{}': {}",
                path.display(),
                e
            );
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
        info!("Настройки сохранены. Некоторые изменения (горячие клавиши) вступят в силу после перезапуска.");
    }

    fn handle_tab_mode(&mut self, pressed: bool) -> Command<Message> {
        if pressed && !self.tab_mode_active {
            self.tab_mode_active = true;
            
            let (screen_w, _screen_h) = xcap::Monitor::all()
                .ok()
                .and_then(|m| m.first().map(|m| (m.width() as f32, m.height() as f32)))
                .unwrap_or((1920.0, 1080.0));

            let tab_width = screen_w * 0.4;
            let tab_height = 80.0;

            Command::batch(vec![
                window::resize(window::Id::MAIN, Size::new(tab_width, tab_height)),
                window::move_to(window::Id::MAIN, Point::new(0.0, 0.0)),
                window::change_level(window::Id::MAIN, window::Level::AlwaysOnTop),
            ])
        } else if !pressed && self.tab_mode_active {
            self.tab_mode_active = false;
            let restore_state = self.pre_tab_mode_state.clone().unwrap_or(WindowModeState {
                size: Size::new(1024.0, 768.0),
                position: Point::new(100.0, 100.0),
            });

            let level = if self.settings.always_on_top {
                window::Level::AlwaysOnTop
            } else {
                window::Level::Normal
            };
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
    fn view_main_tab(&self) -> Element<'_, Message> {
        let left_panel = container(self.view_left_panel())
            .width(Length::FillPortion(2))
            .padding(10)
            .style(theme::Container::Box);

        let right_panel = container(self.view_right_panel())
            .width(Length::FillPortion(1))
            .padding(10)
            .style(theme::Container::Box);

        row![left_panel, right_panel].spacing(10).into()
    }

    fn view_left_panel(&self) -> Element<'_, Message> {
        let title = text("Рейтинг контрпиков").size(24);

        let content = if self.selected_enemies.is_empty() {
            column![text("Выберите врагов на панели справа.")]
        } else {
            let enemies = text(format!("Против: {}", self.selected_enemies.join(", ")));
            let optimal_team_title = text("Оптимальная команда:").size(18);

            let optimal_team_icons = self.optimal_team.iter().fold(row![].spacing(5), |r, hero_name| {
                if let Some(handle) = self.hero_icons.get(hero_name) {
                    r.push(image(handle.clone()).width(Length::Fixed(48.0)))
                } else {
                    r.push(text(hero_name))
                }
            });

            let ratings_title = text("Полный рейтинг героев:").size(18);
            let ratings_list = scrollable(
                column(
                    self.calculated_rating
                        .iter()
                        .map(|(hero, score)| text(format!("{:<20}: {:.2}", hero, score)).into())
                        .collect::<Vec<_>>(),
                )
                .spacing(5),
            );

            column![
                enemies,
                optimal_team_title,
                optimal_team_icons,
                ratings_title,
                ratings_list
            ]
            .spacing(10)
        };

        column![title, content].spacing(15).into()
    }

    fn view_right_panel(&self) -> Element<'_, Message> {
        let title = text("Вражеская команда").size(24);

        let rec_state = self.recognition_manager.as_ref().map(|m| m.get_state());
        let (rec_button_text, is_recognizing) = match rec_state {
            Some(RecognitionState::Recognizing) => ("Распознавание...", true),
            _ => ("Распознать героев", false),
        };

        let mut rec_button = button(rec_button_text);
        if !is_recognizing {
            rec_button = rec_button.on_press(Message::StartRecognition);
        }

        let control_buttons =
            row![rec_button, button("Очистить").on_press(Message::ClearSelection)].spacing(10);

        let hero_grid = scrollable(
            self.all_hero_names
                .chunks(4)
                .fold(column![].spacing(5), |cols, chunk| {
                    let mut hero_row = row![].spacing(5).align_items(Alignment::Center);
                    for hero in chunk {
                        let is_selected = self.selected_enemies.contains(hero);
                        
                        let button_content: Element<'_, Message> = 
                            if let Some(handle) = self.hero_icons.get(hero) {
                                image(handle.clone()).width(Length::Fixed(48.0)).height(Length::Fixed(48.0)).into()
                            } else {
                                text(hero).size(12).into()
                            };

                        hero_row = hero_row.push(
                            button(container(button_content).center_x().center_y())
                                .style(if is_selected {
                                    theme::Button::Primary
                                } else {
                                    theme::Button::Secondary
                                })
                                .on_press(Message::ToggleHero(hero.clone()))
                                .width(Length::Fill)
                                .height(Length::Fixed(56.0))
                                .padding(4),
                        );
                    }
                    cols.push(hero_row)
                }),
        );

        column![title, control_buttons, Space::with_height(10), hero_grid]
            .spacing(10)
            .into()
    }

    fn view_settings_tab(&self) -> Element<'_, Message> {
        let title = text("Настройки").size(24);
        let on_top_checkbox =
            checkbox("Поверх всех окон", self.settings.always_on_top).on_toggle(Message::ToggleAlwaysOnTop);

        let opacity_slider = column![
            text(format!(
                "Прозрачность: {:.2}",
                self.settings.window_opacity
            )),
            slider(
                0.1..=1.0,
                self.settings.window_opacity,
                Message::OpacityChanged
            )
            .step(0.01)
        ]
        .spacing(5);

        let save_button = button("Сохранить настройки").on_press(Message::SaveSettings);

        column![title, on_top_checkbox, opacity_slider, save_button]
            .spacing(20)            .align_items(Alignment::Start)
            .into()
    }
}

// --- Асинхронная загрузка данных ---
async fn load_data_async() -> (
    Result<AllHeroesData, String>,
    Result<HeroRoles, String>,
    HashMap<String, image::Handle>,
) {
    let data_res = data_loader::load_matchups_from_json(
        "database/marvel_rivals_stats_20250810-055947.json",
    )
    .map_err(|e| format!("Ошибка загрузки данных героев: {}", e));

    let roles_res =
        data_loader::load_roles_from_python_file("database/roles_and_groups.py")
            .map_err(|e| format!("Ошибка загрузки ролей: {}", e));

    let hero_names: Vec<String> = if let Ok(data) = &data_res {
        data.keys().cloned().collect()
    } else {
        Vec::new()
    };
    let icons = image_loader::load_hero_icons(&hero_names);

    (data_res, roles_res, icons)
}