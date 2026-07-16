import os
import re
import time
import logging
import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_icons.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rivals_icons")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ICONS_DIR = os.path.join(PROJECT_ROOT, "overwolf_app", "resources", "heroes_icons")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://rivalsmeta.com/'
}

ROLE_TO_DIRNAME = {
    'Vanguard': 'vanguard',
    'Duelist': 'duelist',
    'Strategist': 'strategist',
}


def init_browser(playwright):
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--start-maximized',
            '--no-sandbox',
            '--disable-infobars'
        ]
    )
    context = browser.new_context(
        viewport=None,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        locale='en-US'
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
    """)
    page = context.new_page()
    page.set_default_timeout(30000)
    return browser, context, page


def safe_goto(page, url):
    try:
        logger.info(f"Переход на {url}")
        page.goto(url, wait_until='commit', timeout=30000)
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 300)")
        return True
    except Exception as e:
        logger.error(f"Ошибка перехода: {e}")
        return False


def get_heroes_icons(page, season="1"):
    logger.info(f"--- Сбор иконок героев (Сезон {season}) ---")
    if not safe_goto(page, "https://rivalsmeta.com/characters"):
        return []

    try:
        page.wait_for_selector('table', timeout=20000)

        season_select = page.query_selector('#season_filter')
        if season_select:
            options = season_select.query_selector_all('option')
            season_value = None
            for option in options:
                if season in option.text_content().strip():
                    season_value = option.get_attribute('value')
                    break
            if season_value:
                season_select.select_option(value=season_value)
                logger.info(f"Сезон {season} выбран. Ждем обновления...")
                time.sleep(3)
                page.wait_for_selector('table')

        heroes = page.evaluate(r'''() => {
            const heroes = [];
            const table = document.querySelector('table');
            if (!table) return heroes;
            const rows = table.querySelectorAll('tbody tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) continue;
                const name = cells[0].textContent.trim().replace(/\s+/g, ' ').trim();
                if (!name || name === 'Hero') continue;

                let role = '';
                const roleImg = cells[1].querySelector('img.hero-class');
                if (roleImg) {
                    const src = roleImg.getAttribute('src') || '';
                    const match = src.match(/\/images\/([a-z_-]+)\.png/i);
                    if (match) {
                        role = match[1].charAt(0).toUpperCase() + match[1].slice(1);
                    }
                }
                if (!role) role = cells[1].textContent.trim();

                const heroImg = cells[0].querySelector('img');
                const imgSrc = heroImg ? (heroImg.getAttribute('src') || '') : '';

                const urlName = name.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '_').replace(/^-+|-+$/g, '');

                heroes.push({ display_name: name, url_name: urlName, role: role, img_src: imgSrc });
            }
            return heroes;
        }''')

        valid = [h for h in heroes if h.get('display_name') and h.get('img_src')]
        logger.info(f"Найдено {len(valid)} героев с иконками.")
        return valid
    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
        return []


def download_icon(h, index, total):
    img_src = h['img_src']
    if img_src.startswith('//'):
        img_src = 'https:' + img_src
    elif img_src.startswith('/'):
        img_src = 'https://rivalsmeta.com' + img_src

    filename = f"{h['url_name']}.png"
    out_path = os.path.join(ICONS_DIR, filename)

    if os.path.exists(out_path):
        logger.info(f"[{index+1}/{total}] Пропуск (уже есть): {filename}")
        return True

    try:
        resp = requests.get(img_src, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(out_path, 'wb') as f:
            f.write(resp.content)
        logger.info(f"[{index+1}/{total}] Сохранено: {filename} ({len(resp.content)} байт)")
        return True
    except Exception as e:
        logger.error(f"[{index+1}/{total}] Ошибка загрузки {h['display_name']} ({img_src}): {e}")
        return False


def main(season="9.0"):
    logger.info(f"=== ЗАПУСК СКРИПТА ИКОНОК (СЕЗОН {season}) ===")
    os.makedirs(ICONS_DIR, exist_ok=True)

    playwright = sync_playwright().start()
    browser, context, page = init_browser(playwright)

    try:
        heroes = get_heroes_icons(page, season)
        if not heroes:
            logger.error("Герои не найдены. Выход.")
            return

        ok = 0
        for i, h in enumerate(heroes):
            if download_icon(h, i, len(heroes)):
                ok += 1
            time.sleep(0.5)

        logger.info(f"=== ГОТОВО: загружено {ok}/{len(heroes)} иконок ===")
    except Exception as e:
        logger.exception("Критическая ошибка")
    finally:
        context.close()
        browser.close()
        playwright.stop()


if __name__ == "__main__":
    main(season="9.0")
