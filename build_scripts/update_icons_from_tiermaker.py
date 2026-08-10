import glob
import json
import os
import re
import time
import urllib.parse
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_tiermaker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tiermaker_icons")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
STAGING_DIR = os.path.join(SCRIPT_DIR, "tiermaker_icons")
DB_DIR = os.path.join(PROJECT_ROOT, "overwolf_app", "database", "stats")
ICONS_DIR = os.path.join(PROJECT_ROOT, "overwolf_app", "resources", "heroes_icons")

TIERMAKER_TEMPLATE_URL = "https://tiermaker.com/create/marvel-rivals---all-heroes---including-moon-knight-2053"
TIERMAKER_TEMPLATE_SLUG = "marvel-rivals---all-heroes---including-moon-knight-2053"
TIERMAKER_DEFAULT_VARIATION = "3297493"
TIERMAKER_DEFAULT_LAST_EDITED = "2026-08-06 20:37:31"

TIERMAKER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': TIERMAKER_TEMPLATE_URL
}

ROLE_ORDER = ["Vanguard", "Duelist", "Strategist"]

# Автор шаблона на TierMaker подписал иконку без "The", поэтому герой сортируется как "Punisher".
SORT_KEY_OVERRIDES = {
    "The Punisher": "Punisher",
}


def fetch_tiermaker_config():
    """Достает dateLastEdited и variation из HTML страницы шаблона (с фоллбэком на хардкод)."""
    try:
        resp = requests.get(TIERMAKER_TEMPLATE_URL, headers=TIERMAKER_HEADERS, timeout=30)
        html = resp.text
        m = re.search(r'dateLastEdited\s*=\s*"([^"]+)"', html)
        last_edited = m.group(1) if m else TIERMAKER_DEFAULT_LAST_EDITED
        m = re.search(r'tierSystem\.initList\(\s*"",\s*"[^"]+",\s*"(\d+)"\s*\)', html)
        variation = m.group(1) if m else TIERMAKER_DEFAULT_VARIATION
        logger.info(f"TierMaker config: lastEdited={last_edited}, variation={variation}")
        return last_edited, variation
    except Exception as e:
        logger.warning(f"Не удалось спарсить конфиг со страницы TierMaker ({e}), беру дефолтный.")
        return TIERMAKER_DEFAULT_LAST_EDITED, TIERMAKER_DEFAULT_VARIATION


def get_tiermaker_items():
    """Запрашивает API TierMaker и возвращает список {id, src} в порядке карусели шаблона."""
    last_edited, variation = fetch_tiermaker_config()
    api_url = (
        f"https://tiermaker.com/api/?type=templates-v2"
        f"&id={TIERMAKER_TEMPLATE_SLUG}"
        f"&lastEdited={urllib.parse.quote(last_edited)}"
        f"&variation={variation}"
    )
    logger.info(f"TierMaker API: {api_url}")
    resp = requests.get(api_url, headers=TIERMAKER_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    items = []
    for entry in data[1:]:  # data[0] — имя/путь набора
        if isinstance(entry, dict):
            items.append({'id': entry.get('id'), 'src': entry.get('src')})
        else:
            items.append({'id': len(items) + 1, 'src': entry})
    logger.info(f"TierMaker: получено {len(items)} иконок.")
    return items


def get_db_heroes():
    """Читает роли героев из актуальной базы stats (latest.json -> current -> stats файл)."""
    latest_path = os.path.join(DB_DIR, "latest.json")
    current_name = None
    if os.path.exists(latest_path):
        with open(latest_path, encoding="utf-8") as f:
            current_name = json.load(f).get("current")

    stats_path = os.path.join(DB_DIR, current_name) if current_name else None
    if not stats_path or not os.path.exists(stats_path):
        matches = sorted(glob.glob(os.path.join(DB_DIR, "marvel_rivals_stats_*.json")))
        stats_path = matches[-1] if matches else None

    if not stats_path:
        raise FileNotFoundError(f"Не найден stats-файл базы в {DB_DIR}")

    with open(stats_path, encoding="utf-8") as f:
        data = json.load(f)
    heroes = {name: h.get("role") for name, h in data["heroes"].items()}
    logger.info(f"База: {os.path.basename(stats_path)} — героев с ролями: {len(heroes)}")
    return heroes


def build_ordered_names(heroes):
    """Группирует героев по ролям (Vanguard -> Duelist -> Strategist) и сортирует по алфавиту."""
    by_role = {role: [] for role in ROLE_ORDER}
    unknown = []
    for name, role in heroes.items():
        if role in by_role:
            by_role[role].append(name)
        else:
            unknown.append(name)

    ordered = []
    for role in ROLE_ORDER:
        ordered.extend(sorted(by_role[role], key=lambda n: SORT_KEY_OVERRIDES.get(n, n)))
    if unknown:
        logger.warning(f"Герои без/с неизвестной ролью (добавлены в конец): {unknown}")
        ordered.extend(sorted(unknown, key=lambda n: SORT_KEY_OVERRIDES.get(n, n)))
    return ordered


def hero_icon_name(hero_name):
    """Порт heroIconName из logic.js:143 — имя файла как в overwolf_app/resources/heroes_icons."""
    if not hero_name:
        return ""
    formatted = hero_name.lower().strip()
    formatted = re.sub(r'\s*&\s*', ' ', formatted)
    formatted = re.sub(r'\(([^)]+)\)', r' \1', formatted)
    formatted = re.sub(r'[^\w-]+', ' ', formatted).strip()
    formatted = re.sub(r'[\s-]+', '_', formatted)
    return formatted


def download_icon(item, out_path, force=False):
    """Качает одну иконку по ссылке item['src'] в out_path."""
    src = item['src']
    if src.startswith('//'):
        src = 'https:' + src
    elif src.startswith('/'):
        src = 'https://tiermaker.com' + src

    if not force and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return "skip"

    try:
        resp = requests.get(src, headers=TIERMAKER_HEADERS, timeout=30)
        resp.raise_for_status()
        with open(out_path, 'wb') as f:
            f.write(resp.content)
        return "ok"
    except Exception as e:
        logger.error(f"Ошибка загрузки {os.path.basename(out_path)} ({src}): {e}")
        return "err"


def main(force=False):
    items = get_tiermaker_items()
    if not items:
        logger.error("TierMaker: иконки не получены. Выход.")
        return

    heroes = get_db_heroes()
    names = build_ordered_names(heroes)

    if len(names) != len(items):
        logger.error(
            f"НЕСОВПАДЕНИЕ КОЛИЧЕСТВА: база {len(names)} героев, TierMaker {len(items)} иконок. "
            "Порядок/сортировка не применимы. Выход."
        )
        return

    logger.info(f"Всего позиций: {len(names)} — совпадает.")

    os.makedirs(STAGING_DIR, exist_ok=True)
    existing_local = set(os.listdir(ICONS_DIR)) if os.path.isdir(ICONS_DIR) else set()

    ok = skipped = errs = 0
    new_vs_local = []
    for i, (item, name) in enumerate(zip(items, names)):
        filename = f"{hero_icon_name(name)}.png"
        out_path = os.path.join(STAGING_DIR, filename)
        status = download_icon(item, out_path, force=force)
        if status == "ok":
            ok += 1
            logger.info(f"[{i+1}/{len(names)}] Сохранено: {filename} (id={item.get('id')})")
        elif status == "skip":
            skipped += 1
        else:
            errs += 1
        if filename not in existing_local:
            new_vs_local.append(filename)
        time.sleep(0.3)

    logger.info(f"=== ИТОГ: сохранено {ok}, пропущено (уже есть) {skipped}, ошибок {errs} ===")
    logger.info(f"Превью: позиция -> герой -> файл")
    for i, (item, name) in enumerate(zip(items, names)):
        logger.info(f"  {i+1:>2}. {name} -> {hero_icon_name(name)}.png (id={item.get('id')})")
    if new_vs_local:
        logger.info(f"Нет локально в heroes_icons (появятся при деплое): {new_vs_local}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Скачивание иконок героев с TierMaker с именами из базы")
    parser.add_argument("--force", action="store_true",
                        help="перезаписывать уже скачанные иконки в staging-папке")
    args = parser.parse_args()
    main(force=args.force)
