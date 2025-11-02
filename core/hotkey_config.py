# File: core/hotkey_config.py

# Значения по умолчанию для горячих клавиш
DEFAULT_HOTKEYS = {
    "move_cursor_up": "tab+up",
    "move_cursor_down": "tab+down",
    "move_cursor_left": "tab+left",
    "move_cursor_right": "tab+right",
    "toggle_selection": "tab+2",
    "recognize_heroes": "tab+/",
    "clear_all": "tab+subtract",
    "copy_team": "tab+1",
    "debug_capture": "tab+3",
    # ИЗМЕНЕНИЕ: Новые хоткеи для управления картой с цифрами по умолчанию
    "cycle_map_forward": "tab+8",  # Tab + 8 для следующей карты
    "cycle_map_backward": "tab+9",  # Tab + 9 для предыдущей карты
    "reset_map": "tab+0",  # Tab + 0 для сброса карты
}

# Конфигурация действий для горячих клавиш
HOTKEY_ACTIONS_CONFIG = {
    "move_cursor_up": {"desc_key": "hotkey_desc_navigation_up", "signal_name": "action_move_cursor_up", "suppress": True},
    "move_cursor_down": {"desc_key": "hotkey_desc_navigation_down", "signal_name": "action_move_cursor_down", "suppress": True},
    "move_cursor_left": {"desc_key": "hotkey_desc_navigation_left", "signal_name": "action_move_cursor_left", "suppress": True},
    "move_cursor_right": {"desc_key": "hotkey_desc_navigation_right", "signal_name": "action_move_cursor_right", "suppress": True},
    "toggle_selection": {"desc_key": "hotkey_desc_select", "signal_name": "action_toggle_selection", "suppress": True},
    "recognize_heroes": {"desc_key": "hotkey_desc_recognize", "signal_name": "action_recognize_heroes", "suppress": True},
    "clear_all": {"desc_key": "hotkey_desc_clear", "signal_name": "action_clear_all", "suppress": True},
    "copy_team": {"desc_key": "hotkey_desc_copy_team", "signal_name": "action_copy_team", "suppress": True},
    "debug_capture": {"desc_key": "hotkey_desc_debug_screenshot", "signal_name": "action_debug_capture", "suppress": True},
    # ИЗМЕНЕНИЕ: Новые действия для управления картой
    "cycle_map_forward": {"desc_key": "hotkey_desc_cycle_map_forward", "signal_name": "action_cycle_map_forward", "suppress": True},
    "cycle_map_backward": {"desc_key": "hotkey_desc_cycle_map_backward", "signal_name": "action_cycle_map_backward", "suppress": True},
    "reset_map": {"desc_key": "hotkey_desc_reset_map", "signal_name": "action_reset_map", "suppress": True},
}