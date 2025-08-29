#![cfg(target_os = "windows")]

//! Модуль для управления окнами через Win32 API
//! Обеспечивает функциональность always-on-top overlay окна даже когда фокус не на приложении

use windows::Win32::{
    Foundation::{HWND, RECT, BOOL},
    UI::{
        WindowsAndMessaging::{
            FindWindowA, GetWindowRect, SetWindowPos, ShowWindow,
            SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE,
            SW_SHOW, SW_HIDE, HWND_TOPMOST, HWND_NOTOPMOST,
        },
    },
};

/// Структура для управления окном через Win32 API
pub struct WindowManager {
    window_handle: Option<HWND>,
    is_topmost: bool,
}

impl WindowManager {
    /// Создает новый менеджер окон
    pub fn new() -> Self {
        Self {
            window_handle: None,
            is_topmost: false,
        }
    }

    /// Устанавливает handle окна для управления
    /// Нужно вызвать после инициализации Iced окна
    pub fn set_window_handle(&mut self, title_substring: &str) -> bool {
        log::debug!("Ищем окно с substring: '{}'", title_substring);

        use windows::core::PCSTR;

        let mut found_window = None;

        if title_substring.is_empty() {
            // При пустой строке ищем первые подходящие окна (обычно это наше приложение)
            let keywords = ["Rivals", "Iced", "Counter"];

            for keyword in &keywords {
                log::debug!("Пробуем найти окно с keyword: '{}'", keyword);
                let title_pcstr = PCSTR::from_raw(keyword.as_ptr());
                let hwnd = unsafe { FindWindowA(PCSTR::null(), title_pcstr) };
                if hwnd.0 != 0 {
                    found_window = Some(hwnd);
                    log::info!("Найдено окно с keyword '{}' , handle: {:?}", keyword, hwnd);
                    break;
                }
            }
        } else {
            // Конвертируем строку в PCSTR и ищем точное совпадение
            let title_pcstr = PCSTR::from_raw(title_substring.as_ptr());
            let hwnd = unsafe { FindWindowA(PCSTR::null(), title_pcstr) };
            if hwnd.0 != 0 {
                found_window = Some(hwnd);
            }
        }

        if let Some(hwnd) = found_window {
            self.window_handle = Some(hwnd);
            log::info!("Окно find успешно, handle: {:?}", hwnd);
            true
        } else {
            log::warn!("Окно с substring '{}' не найдено", title_substring);
            false
        }
    }

    /// Возвращает текущий handle окна
    pub fn get_window_handle(&self) -> Option<HWND> {
        self.window_handle
    }

    /// Делает окно всегда поверх всех окон
    pub fn set_always_on_top(&mut self, always_on_top: bool) -> Result<(), String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен. Вызовите set_window_handle() сначала.".to_string()
        })?;

        unsafe {
            let insert_after_hwnd = if always_on_top {
                log::debug!("Устанавливаем окно на самый верх");
                self.is_topmost = true;
                HWND_TOPMOST
            } else {
                log::debug!("Убираем окно с самого верха");
                self.is_topmost = false;
                HWND_NOTOPMOST
            };

            let result = SetWindowPos(
                hwnd,
                insert_after_hwnd,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            );

            match result {
                Ok(()) => {
                    log::debug!(
                        "SetWindowPos called to update topmost status to: {}",
                        always_on_top
                    );
                    Ok(())
                }
                Err(e) => Err(format!("Не удалось обновить позицию окна: {:?}", e)),
            }
        }
    }

    /// Показывает или скрывает окно
    pub fn show_window(&self, show: bool) -> Result<(), String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен".to_string()
        })?;

        let cmd_show = if show { SW_SHOW } else { SW_HIDE };

        unsafe {
            let result: BOOL = ShowWindow(hwnd, cmd_show);
            // ShowWindow возвращает TRUE если окно ранее было скрыто, FALSE если оно было видимо
            // В данном контексте нас интересует что функция выполнилась
            log::debug!("Окно {}: {:?} (ShowWindow result: {})",
                if show { "показано" } else { "скрыто" }, hwnd, result.0);
            Ok(())
        }
    }

    /// Возвращает текущий always-on-top статус
    pub fn is_always_on_top(&self) -> bool {
        self.is_topmost
    }

    /// Перемещает окно в указанную позицию через Win32 API
    pub fn move_window(&self, x: i32, y: i32) -> Result<(), String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен".to_string()
        })?;

        unsafe {
            let result = SetWindowPos(
                hwnd,
                if self.is_topmost { HWND_TOPMOST } else { HWND(0) },
                x, y, 0, 0,
                SWP_NOSIZE | SWP_NOACTIVATE
            );

            match result {
                Ok(()) => {
                    log::debug!("Окно перемещено в позицию ({}, {}) через Win32 API", x, y);
                    Ok(())
                }
                Err(e) => Err(format!("Не удалось переместить окно: {:?}", e)),
            }
        }
    }

    /// Изменяет размер окна через Win32 API
    pub fn resize_window(&self, width: i32, height: i32) -> Result<(), String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен".to_string()
        })?;

        unsafe {
            let result = SetWindowPos(
                hwnd,
                if self.is_topmost { HWND_TOPMOST } else { HWND(0) },
                0, 0, width, height,
                SWP_NOMOVE | SWP_NOACTIVATE
            );

            match result {
                Ok(()) => {
                    log::debug!("Размер окна изменен на {}x{} через Win32 API", width, height);
                    Ok(())
                }
                Err(e) => Err(format!("Не удалось изменить размер окна: {:?}", e)),
            }
        }
    }

    /// Изменяет и позицию, и размер окна через Win32 API
    pub fn move_resize_window(&self, x: i32, y: i32, width: i32, height: i32) -> Result<(), String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен".to_string()
        })?;

        unsafe {
            let result = SetWindowPos(
                hwnd,
                if self.is_topmost { HWND_TOPMOST } else { HWND(0) },
                x, y, width, height,
                SWP_NOACTIVATE
            );

            match result {
                Ok(()) => {
                    log::debug!("Окно перемещено и изменено через Win32 API: ({}, {}) {}x{}", x, y, width, height);
                    Ok(())
                }
                Err(e) => Err(format!("Не удалось переместить и изменить размер окна: {:?}", e)),
            }
        }
    }

    /// Получает текущие координаты и размер окна
    pub fn get_window_rect(&self) -> Result<RECT, String> {
        let hwnd = self.window_handle.ok_or_else(|| {
            "Window handle не установлен".to_string()
        })?;

        let mut rect = RECT::default();

        unsafe {
            match GetWindowRect(hwnd, &mut rect) {
                Ok(_) => Ok(rect),
                Err(e) => Err(format!("Не удалось получить размер окна: {:?}", e)),
            }
        }
    }
}

impl Default for WindowManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Создает глобальный экземпляр WindowManager для использования в приложении
/// Позволяет управлять overlay из любого места программы
static mut WINDOW_MANAGER: Option<WindowManager> = None;

pub fn get_window_manager() -> &'static mut WindowManager {
    unsafe {
        WINDOW_MANAGER.get_or_insert_with(WindowManager::new)
    }
}

/// Инициализирует глобальный менеджер окон с указанным заголовком окна
pub fn init_window_manager(window_title_substring: &str) -> Result<(), String> {
    unsafe {
        WINDOW_MANAGER = Some(WindowManager::new());
        if let Some(manager) = WINDOW_MANAGER.as_mut() {
            if manager.set_window_handle(window_title_substring) {
                Ok(())
            } else {
                Err(format!("Не удалось найти окно с substring '{}'", window_title_substring))
            }
        } else {
            Err("Не удалось инициализировать менеджер окон".to_string())
        }
    }
}

/// Быстрая функция для активации overlay режима
/// Устанавливает окно поверх всех и показывает его
pub fn activate_overlay_mode() -> Result<(), String> {
    let manager = get_window_manager();
    manager.set_always_on_top(true)?;
    manager.show_window(true)?;
    Ok(())
}

/// Быстрая функция для деактивации overlay режима
/// Снимает always-on-top статус, но оставляет окно видимым
pub fn deactivate_overlay_mode() -> Result<(), String> {
    let manager = get_window_manager();
    manager.set_always_on_top(false)?;
    Ok(())
}

/// Быстрая функция для перемещения окна через Win32 API
pub fn move_window(x: i32, y: i32) -> Result<(), String> {
    let manager = get_window_manager();
    manager.move_window(x, y)
}

/// Быстрая функция для изменения размера окна через Win32 API
pub fn resize_window(width: i32, height: i32) -> Result<(), String> {
    let manager = get_window_manager();
    manager.resize_window(width, height)
}

/// Быстрая функция для перемещения и изменения размера окна через Win32 API
pub fn move_resize_window(x: i32, y: i32, width: i32, height: i32) -> Result<(), String> {
    let manager = get_window_manager();
    manager.move_resize_window(x, y, width, height)
}