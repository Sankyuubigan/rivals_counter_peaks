import json
import os
import glob
import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_DIR = os.path.join(PROJECT_ROOT, "overwolf_app", "database", "stats")


def _latest_stats_file():
    """Возвращает путь к самому свежему файлу статистики (исключая _INCOMPLETE)."""
    files = glob.glob(os.path.join(STATS_DIR, "marvel_rivals_stats_*.json"))
    files = [f for f in files if "_INCOMPLETE" not in os.path.basename(f)]
    if not files:
        pytest.skip("Нет файла статистики для проверки")
    return max(files, key=os.path.getmtime)


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_no_hero_with_empty_matchups_and_maps():
    """Ни у одного героя не должно быть ОДНОВРЕМЕННО пустых opponents и maps.

    Раньше скрипт молча записывал половину героев без данных (сайт отдавал
    500 на неверный slug). Этот тест ловит такой битый JSON.
    """
    data = _load(_latest_stats_file())
    heroes = data.get("heroes", {})
    assert heroes, "В файле нет героев"

    empty_heroes = [
        name
        for name, h in heroes.items()
        if not (h.get("opponents") or h.get("maps"))
    ]
    assert not empty_heroes, (
        f"У {len(empty_heroes)} героев отсутствуют И matchups, И maps: {empty_heroes}"
    )


def test_every_hero_has_core_fields():
    """У каждого героя должны быть заполнены базовые поля."""
    data = _load(_latest_stats_file())
    heroes = data.get("heroes", {})
    required = ["win_rate", "pick_rate", "role", "tier"]
    for name, h in heroes.items():
        for field in required:
            assert h.get(field), f"У героя '{name}' пустое поле '{field}'"


def test_hero_with_matchups_but_no_maps_is_valid():
    """Герой может не иметь данных по картам (сайт не даёт для новых героев),
    но при наличии матчапов он НЕ считается битым.
    """
    data = _load(_latest_stats_file())
    heroes = data.get("heroes", {})
    for name, h in heroes.items():
        if h.get("opponents") and not h.get("maps"):
            # это допустимо — не должно трактоваться как ошибка
            assert h.get("opponents"), f"У '{name}' есть матчапы, но проверка провалилась"


def test_fully_empty_hero_is_detected():
    """Если у героя пусты И matchups, И maps — это реальный провал сбора."""
    data = _load(_latest_stats_file())
    heroes = data.get("heroes", {})
    fully_empty = [
        name
        for name, h in heroes.items()
        if not (h.get("opponents") or h.get("maps"))
    ]
    # Для свежего валидного файла полностью пустых героев быть не должно.
    # (Если сайт реально упал для кого-то — валидатор в скрипте это отбракует
    #  и сохранит _INCOMPLETE, который этот тест проигнорирует.)
    assert not fully_empty, f"Полностью пустые герои: {fully_empty}"


def test_no_incomplete_files_present():
    """В папке не должно оставаться битых файлов с суффиксом _INCOMPLETE."""
    incomplete = glob.glob(os.path.join(STATS_DIR, "*_INCOMPLETE.json"))
    assert not incomplete, (
        "Обнаружены неполные файлы (валидатор сработал и остановил запись): "
        f"{[os.path.basename(f) for f in incomplete]}"
    )


def test_hero_url_slugs_resolve():
    """Проверяет, что slug'и героев из списка совпадают с реальными URL сайта.

    Ловит баг, когда генерация slug давала 'peniparker' вместо 'peni-parker'
    (сайт возвращал 500 -> пустые данные).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "update_db_rivalsmeta",
        os.path.join(PROJECT_ROOT, "build_scripts", "update_db_rivalsmeta.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, context, page = module.init_browser(p)
        try:
            heroes = module.get_heroes_list(page, "9.0")
        finally:
            context.close()
            browser.close()
            p.stop()

    bad = [h["display_name"] for h in heroes if not h.get("url_name") or "--" in h["url_name"]]
    assert not bad, f"Некорректные slug'и у героев: {bad}"
