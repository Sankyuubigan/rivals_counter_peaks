use iced::{
    widget::{button, checkbox, column, container, row, text, text_input, Space},
    Alignment, Element, Length,
};

use super::iced_app::{IcedApp, Message, get_button_style};

pub fn view_settings_tab(app: &IcedApp) -> Element<'_, Message> {
    // --- General Settings ---
    let general_settings = column![
        text("Общие настройки").size(20),
        checkbox("Поверх всех окон", app.settings.always_on_top)
            .on_toggle(Message::ToggleAlwaysOnTop),
        text("Горячая клавиша для распознавания: TAB + 0").size(16),
    ]
    .spacing(10);

    // --- Screenshot Settings ---
    let screenshot_settings = column![
        text("Настройки скриншотов").size(20),
        checkbox(
            "Сохранять скриншот, если распознано < 6 героев",
            app.settings.save_failed_screenshots
        )
        .on_toggle(Message::ToggleSaveScreenshots),
        row![
            text("Папка для сохранения:").width(Length::Shrink),
            text_input("Путь...", &app.settings.screenshot_path)
                .on_input(Message::ScreenshotPathChanged),
            button("Обзор...").on_press(Message::BrowseScreenshotPath)
        ]
        .spacing(10)
        .align_items(Alignment::Center),
    ]
    .spacing(10);

    // --- Save Button ---
    let save_button = button("Сохранить настройки")
        .style(get_button_style(true))
        .on_press(Message::SaveSettings);

    // --- Layout ---
    let content = column![
        general_settings,
        Space::with_height(20),
        screenshot_settings,
        Space::with_height(Length::Fill),
        save_button
    ]
    .spacing(15)
    .padding(20);

    container(content).width(Length::Fill).height(Length::Fill).into()
}