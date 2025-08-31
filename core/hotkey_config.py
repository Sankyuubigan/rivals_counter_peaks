# File: core/hotkey_config.py

# Значения по умолчанию для горячих клавиш
DEFAULT_HOTKEYS = {
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+num_0",
    "toggle_mode": "tab+num_multiply",
    "recognize_heroes": "tab+num_divide", # Убедились, что здесь tab+num_divide
    "clear_all": "tab+num_subtract",
    "copy_team": "tab+num_1",
    "debug_capture": "tab+num_3",
    "decrease_opacity": "tab+num_4",
    "increase_opacity": "tab+num_6",
}

# Конфигурация действий для горячих клавиш
HOTKEY_ACTIONS_CONFIG = {
    "move_cursor_up": {"desc_key": "hotkey_desc_navigation_up", "signal_name": "action_move_cursor_up", "suppress": True},
    "move_cursor_down": {"desc_key": "hotkey_desc_navigation_down", "signal_name": "action_move_cursor_down", "suppress": True},
    "move_cursor_left": {"desc_key": "hotkey_desc_navigation_left", "signal_name": "action_move_cursor_left", "suppress": True},
    "move_cursor_right": {"desc_key": "hotkey_desc_navigation_right", "signal_name": "action_move_cursor_right", "suppress": True},
    "toggle_selection": {"desc_key": "hotkey_desc_select", "signal_name": "action_toggle_selection", "suppress": True},
    "toggle_mode": {"desc_key": "hotkey_desc_toggle_mode", "signal_name": "action_toggle_mode", "suppress": True},
    "recognize_heroes": {"desc_key": "hotkey_desc_recognize", "signal_name": "action_recognize_heroes", "suppress": True}, # suppress=True, так как комбинация специфична
    "clear_all": {"desc_key": "hotkey_desc_clear", "signal_name": "action_clear_all", "suppress": True},
    "copy_team": {"desc_key": "hotkey_desc_copy_team", "signal_name": "action_copy_team", "suppress": True},
    "debug_capture": {"desc_key": "hotkey_desc_debug_screenshot", "signal_name": "action_debug_capture", "suppress": True},
    "decrease_opacity": {"desc_key": "hotkey_desc_decrease_opacity", "signal_name": "action_decrease_opacity", "suppress": True},
    "increase_opacity": {"desc_key": "hotkey_desc_increase_opacity", "signal_name": "action_increase_opacity", "suppress": True},
}