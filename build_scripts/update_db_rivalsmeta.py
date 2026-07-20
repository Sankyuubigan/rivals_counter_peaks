import json
import time
import logging
import random
import re
import os
from playwright.sync_api import sync_playwright

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("rivals_scraper")

# Путь к файлу с маппингом (относительно корня проекта)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GAME_ENTITIES_PATH = os.path.join(PROJECT_ROOT, "database", "game_entities_dict.json")


def load_map_filename_mapping():
    """Загружает маппинг img_filename -> correct_name из game_entities_dict.json."""
    try:
        with open(GAME_ENTITIES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("map_filename_to_name", {})
    except Exception as e:
        logger.error(f"Не удалось загрузить маппинг карт: {e}")
        return {}


def extract_map_filename(img_src):
    """Извлекает имя файла карты (img_map_xxx) из src картинки."""
    if not img_src:
        return None
    match = re.search(r'images/Map/(img_map_\w+)\.png', img_src)
    return match.group(1) if match else None

def init_browser(playwright):
    """Запускает браузер один раз для всей сессии."""
    browser = playwright.chromium.launch(
        headless=False,  # Видимое окно
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
    
    # Скрипт для скрытия автоматизации
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
    """)
    
    page = context.new_page()
    page.set_default_timeout(30000)
    
    return browser, context, page

def safe_goto(page, url):
    """Переходит по URL, игнорируя зависание на рекламе.

    Возвращает код ответа (int) или None при сбое сети.
    """
    try:
        logger.info(f"Переход на {url}")
        # wait_until='commit' ждет только соединения, а не загрузки всей тяжелой рекламы
        response = page.goto(url, wait_until='commit', timeout=30000)

        # Небольшая пауза и скролл, чтобы инициировать загрузку контента
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 300)")
        return response.status if response else None
    except Exception as e:
        logger.error(f"Ошибка перехода: {e}")
        return None

def select_season(page, season, selector='#season_filter'):
    """Выбирает сезон в выпадающем списке (по подстроке в тексте опции)."""
    season_select = page.query_selector(selector)
    if not season_select:
        # Fallback: любой <select> в блоке фильтра Season
        for sel in page.query_selector_all('select'):
            label = sel.evaluate("el => { const l = el.closest('.filter'); return l ? l.textContent : ''; }")
            if 'season' in (label or '').lower():
                season_select = sel
                break
    if not season_select:
        return False

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
        return True
    return False


def get_teamups_data(page, season="1"):
    """Получает данные о тим апах (разметка сезона 9+: .teamup-grid > article.teamup-card)."""
    logger.info("--- Сбор Team-Ups ---")
    if not safe_goto(page, "https://rivalsmeta.com/team-ups"):
        return []

    try:
        if not page.wait_for_selector('.teamup-grid', timeout=15000):
            logger.warning("Контейнер .teamup-grid не найден.")
            return []

        # Выбираем нужный сезон (Season 9 и т.д.)
        select_season(page, season)
        page.wait_for_selector('.teamup-grid', timeout=15000)

        teamups_data = page.evaluate('''() => {
            const teamups = [];
            const cards = document.querySelectorAll('.teamup-grid > article.teamup-card');
            cards.forEach(card => {
                const nameEl = card.querySelector('.card-head .name');
                if (!nameEl) return;
                const name = nameEl.textContent.trim();

                // Тир: из класса tier-X или из .tier-letter
                let tier = 'Unknown';
                const tierClass = Array.from(card.classList).find(c => c.startsWith('tier-') && c !== 'teamup-card');
                if (tierClass) tier = tierClass.replace('tier-', '').toUpperCase();
                const tierLetterEl = card.querySelector('.tier-letter');
                if (tierLetterEl && tier === 'Unknown') tier = tierLetterEl.textContent.trim().toUpperCase();

                // Win Rate
                const wrEl = card.querySelector('.card-stats .val.wr');
                const win_rate = wrEl ? wrEl.textContent.trim() : '';

                // Герои (slug из href ссылок a.v-hero)
                const heroSlugs = Array.from(card.querySelectorAll('.v-heroes a.v-hero'))
                    .map(a => {
                        const href = a.getAttribute('href') || '';
                        const parts = href.split('/').filter(Boolean);
                        return parts[parts.length - 1] || '';
                    })
                    .filter(Boolean);

                if (heroSlugs.length >= 1) {
                    teamups.push({ name, tier, win_rate, heroes: heroSlugs });
                }
            });
            return teamups;
        }''')
        logger.info(f"Найдено {len(teamups_data)} тим-апов.")
        return teamups_data
    except Exception as e:
        logger.error(f"Ошибка парсинга teamups: {e}")
        return []

def get_heroes_list(page, season="1"):
    """Получает список героев."""
    logger.info(f"--- Сбор списка героев (Сезон {season}) ---")
    if not safe_goto(page, "https://rivalsmeta.com/characters"):
        return []

    try:
        # Ждем таблицу, игнорируя остальное
        page.wait_for_selector('table', timeout=20000)
        
        # Выбор сезона
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
                page.wait_for_selector('table') # Ждем перерисовки
        
        heroes_data = page.evaluate(r'''() => {
            const heroes = [];
            const table = document.querySelector('table');
            if (!table) return heroes;
            
            const rows = table.querySelectorAll('tbody tr');
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const cells = row.querySelectorAll('td');
                
                if (cells.length >= 7) {
                    let heroName = cells[0].textContent.trim().replace(/\\s+/g, ' ').trim();

                    // Берём РЕАЛЬНЫЙ slug из ссылки на героя в таблице,
                    // а не генерируем из имени. Сайт сам знает правильный
                    // URL (например /characters/peni-parker), и генерация
                    // из имени ломалась (давала "peniparker") -> 500 ошибка.
                    let urlName = '';
                    const heroLink = cells[0].querySelector('a');
                    if (heroLink) {
                        const href = heroLink.getAttribute('href') || '';
                        const parts = href.split('/').filter(Boolean);
                        // последний сегмент пути и есть slug
                        urlName = parts[parts.length - 1] || '';
                    }
                    if (!urlName) {
                        // Fallback: генерация из имени, если ссылки нет
                        urlName = heroName.toLowerCase().replace(/[^a-z0-9\\s-]/g, '').replace(/\\s+/g, '-').replace(/^-+|-+$/g, '');
                    }
                    
                    let role = '';
                    const roleImg = cells[1].querySelector('img.hero-class');
                    if (roleImg) {
                        // Роль извлекаем из имени файла в src, т.к. alt содержит имя героя (баг сайта)
                        // Пример: /images/vanguard.png -> vanguard
                        const src = roleImg.getAttribute('src') || '';
                        const match = src.match(/\/images\/([a-z_-]+)\.png/i);
                        if (match) {
                            role = match[1].charAt(0).toUpperCase() + match[1].slice(1);
                        }
                    }
                    if (!role) role = cells[1].textContent.trim();
                    
                    heroes.push({
                        display_name: heroName,
                        url_name: urlName,
                        role: role,
                        tier: cells[2].textContent.trim(),
                        win_rate: cells[3].textContent.trim(),
                        pick_rate: cells[4].textContent.trim(),
                        ban_rate: cells[5].textContent.trim(),
                        matches: cells[6].textContent.trim(),
                    });
                }
            }
            return heroes;
        }''')
        
        valid_heroes = [h for h in heroes_data if h.get('display_name') and h['display_name'] != 'Hero']
        logger.info(f"Найдено {len(valid_heroes)} героев.")
        return valid_heroes
    except Exception as e:
        logger.error(f"Ошибка парсинга героев: {e}")
        return []

def wait_for_table(page, timeout=15000, retries=2):
    """Ждёт появления таблицы, с повторными попытками при неудаче.

    Возвращает True, если таблица появилась, иначе False.
    """
    for attempt in range(retries + 1):
        try:
            page.wait_for_selector('table', timeout=timeout, state='attached')
            return True
        except Exception as e:
            if attempt < retries:
                logger.warning(f"Таблица не найдена (попытка {attempt+1}/{retries+1}), повторяем...")
                time.sleep(2)
            else:
                logger.warning(f"Таблица так и не появилась: {e}")
    return False


def get_matchups_and_maps(page, hero_url_name, season="1"):
    """Собирает матчапы и карты для одного героя.

    При 500/таймауте делает reload и повторяет попытки. Если после всех
    попыток данные не собраны — возвращает ok=False (вызывающий код обязан
    остановиться, НЕ записывая битый файл).
    """
    ok = True

    # 1. MATCHUPS
    matchups = []
    url_matchups = f"https://rivalsmeta.com/characters/{hero_url_name}/matchups"
    status = safe_goto(page, url_matchups)
    if status is None:
        logger.error(f"Матчапы {hero_url_name} - сбой сети при переходе")
        ok = False
    elif status >= 400:
        # Сервер вернул ошибку (напр. 500). Пробуем reload несколько раз.
        logger.warning(f"Матчапы {hero_url_name} - сервер вернул {status}, повторяем...")
        recovered = False
        for attempt in range(3):
            time.sleep(3)
            status = safe_goto(page, url_matchups)
            if status and status < 400:
                recovered = True
                break
        if not recovered:
            logger.error(f"Матчапы {hero_url_name} - сервер стабильно возвращает ошибку, данные не получены")
            ok = False
    if ok:
        try:
            if not wait_for_table(page):
                logger.error(f"Матчапы {hero_url_name} - таблица не загрузилась, данные не получены")
                ok = False
            else:
                matchups = page.evaluate(r'''() => {
                    const allMatchups = [];
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headers = Array.from(table.querySelectorAll('th')).map(h => h.textContent.trim().toLowerCase());
                        if (headers.includes('hero') && headers.includes('win rate')) {
                            const rows = table.querySelectorAll('tbody tr');
                            for (const row of rows) {
                                const cells = row.querySelectorAll('td');
                                if (cells.length < 4) continue;

                                // Имя оппонента хранится в alt первой <img> внутри блока .matchup .cha
                                // (левая, не .active сторона). Текст ячейки — это только "1288W VS1759W".
                                let opponentName = '';
                                const matchupEl = cells[0].querySelector('.matchup');
                                if (matchupEl) {
                                    const chaEls = matchupEl.querySelectorAll('.cha');
                                    // первая .cha — оппонент, .active .cha — текущий герой
                                    let oppCha = null;
                                    for (const cha of chaEls) {
                                        if (!cha.classList.contains('active')) { oppCha = cha; break; }
                                    }
                                    if (!oppCha && chaEls.length > 0) oppCha = chaEls[0];
                                    if (oppCha) {
                                        const img = oppCha.querySelector('img');
                                        if (img) opponentName = img.getAttribute('alt') || '';
                                    }
                                }
                                if (!opponentName) {
                                    const img = cells[0].querySelector('img');
                                    if (img) opponentName = img.getAttribute('alt') || '';
                                }
                                opponentName = (opponentName || '').trim();
                                if (opponentName) {
                                    allMatchups.push({
                                        opponent: opponentName,
                                        win_rate: cells[1].textContent.trim(),
                                        difference: cells[2].textContent.trim(),
                                        matches: cells[3].textContent.trim()
                                    });
                                }
                            }
                        }
                    }
                    return allMatchups;
                }''')
        except Exception as e:
            logger.error(f"Ошибка парсинга матчапов {hero_url_name}: {e}")
            ok = False

    time.sleep(1)

    # 2. MAPS — сохраняем img_map_xxx как map_name
    maps_data = []
    url_maps = f"https://rivalsmeta.com/characters/{hero_url_name}/maps"
    status = safe_goto(page, url_maps)
    if status is None:
        logger.error(f"Карты {hero_url_name} - сбой сети при переходе")
        ok = False
    elif status >= 400:
        logger.warning(f"Карты {hero_url_name} - сервер вернул {status}, повторяем...")
        recovered = False
        for attempt in range(3):
            time.sleep(3)
            status = safe_goto(page, url_maps)
            if status and status < 400:
                recovered = True
                break
        if not recovered:
            logger.error(f"Карты {hero_url_name} - сервер стабильно возвращает ошибку, данные не получены")
            ok = False
    if ok:
        try:
            if not wait_for_table(page):
                # Сайт может не иметь статистики карт для героя (новые герои
                # сезона) — это не провал сбора, matchups всё равно есть.
                logger.warning(f"Карты {hero_url_name} - таблица карт отсутствует (возможно, сайт не даёт данные по картам для этого героя)")
            else:
                maps_data = page.evaluate(r'''() => {
                    const allMaps = [];
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headers = table.querySelectorAll('th');
                        let hasMapHeader = false;
                        for (const header of headers) {
                            if (header.textContent.trim().toLowerCase() === 'map') hasMapHeader = true;
                        }
                        if (hasMapHeader) {
                            const rows = table.querySelectorAll('tbody tr');
                            for (const row of rows) {
                                const nameEl = row.querySelector('td .name') || row.querySelector('td:first-child');
                                const cells = row.querySelectorAll('td');
                                if (nameEl && cells.length >= 3) {
                                    const mapImg = cells[0].querySelector('.image img');
                                    const imgSrc = mapImg ? (mapImg.getAttribute('src') || '') : '';
                                    // Извлекаем img_map_xxx из src
                                    const match = imgSrc.match(/images\/Map\/(img_map_\w+)\.png/);
                                    const mapFilename = match ? match[1] : '';
                                    allMaps.push({
                                        map_name: mapFilename,
                                        matches: cells[1].textContent.trim(),
                                        win_rate: cells[2].textContent.trim()
                                    });
                                }
                            }
                        }
                    }
                    return allMaps;
                }''')
        except Exception as e:
            logger.warning(f"Ошибка парсинга карт {hero_url_name}: {e}")
            ok = False

    # Герой считается собранным, если хотя бы один источник вернул данные.
    # Сайт может не отдавать карты для некоторых героев (новые герои сезона)
    # — это не провал, matchups всё равно используются алгоритмом.
    ok = bool(matchups) or bool(maps_data)
    if not ok:
        logger.error(f"{hero_url_name} - НЕ собрано НИ матчапов, НИ карт (реальный провал)")
    return matchups, maps_data, ok

def save_to_json(data, suffix=""):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"marvel_rivals_stats_{timestamp}{suffix}.json"
    # Сохраняем сразу в целевую папку БД (overwolf_app/database/stats/)
    out_dir = os.path.join(PROJECT_ROOT, "overwolf_app", "database", "stats")
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Сохранено в {filepath}")
    return filepath


def write_latest_index(filename):
    """Пишет database/stats/latest.json с именем самого свежего файла.

    Приложение (logic.js) читает этот индекс, чтобы автоматически
    подхватывать самую свежую базу без правки имён вручную.
    """
    out_dir = os.path.join(PROJECT_ROOT, "overwolf_app", "database", "stats")
    index_path = os.path.join(out_dir, "latest.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({"current": filename}, f, ensure_ascii=False, indent=2)
    logger.info(f"Индекс latest.json обновлён: {filename}")

def main(season="1"):
    logger.info(f"=== ЗАПУСК СКРИПТА (СЕЗОН {season}) ===")
    
    playwright = sync_playwright().start()
    browser, context, page = init_browser(playwright)
    
    try:
        # 1. Тим апы
        teamups = get_teamups_data(page, season)
        time.sleep(2)
        
        # 2. Список героев
        heroes = get_heroes_list(page, season)
        
        if not heroes:
            logger.error("Герои не найдены. Выход.")
            return

        # Индекс: slug героя -> список тим-апов, где он участвует.
        # Нормализуем slug (убираем &, схлопываем дефисы), т.к. url_name героя
        # ("cloak & dagger" -> "cloak--dagger") и slug сайта ("cloak-dagger") могут различаться.
        def norm_slug(s):
            return re.sub(r'-+', '-', s.lower().replace('&', '').replace(' ', '-')).strip('-')

        teamups_by_hero = {}
        for tu in teamups:
            for slug in tu.get("heroes", []):
                teamups_by_hero.setdefault(norm_slug(slug), []).append({
                    "name": tu["name"],
                    "tier": tu["tier"],
                    "win_rate": tu["win_rate"]
                })

        all_data = {'teamups': teamups, 'heroes': {}}
        failed_heroes = []   # герои, по которым НЕ собрано ВООБЩЕ ничего (провал)
        no_maps_heroes = []  # герои, у которых нет карт, но есть матчапы (ок, сайт не даёт)

        # 3. Проход по каждому герою
        for i, hero in enumerate(heroes):
            logger.info(f"[{i+1}/{len(heroes)}] Обработка: {hero['display_name']}")

            matchups, maps, ok = get_matchups_and_maps(page, hero["url_name"], season)

            # Провал только если вообще ничего не собрано (ни матчапов, ни карт).
            # Отсутствие карт при наличии матчапов — допустимо (сайт не даёт
            # данные по картам для некоторых героев), алгоритм это переварит.
            has_data = bool(matchups) or bool(maps)
            if not has_data:
                failed_heroes.append(hero['display_name'])
                logger.error(
                    f"ДАННЫЕ НЕ СОБРАНЫ для {hero['display_name']} "
                    f"(matchups={len(matchups)}, maps={len(maps)})"
                )
            elif not maps:
                no_maps_heroes.append(hero['display_name'])

            all_data["heroes"][hero["display_name"]] = {
                "win_rate": hero["win_rate"],
                "pick_rate": hero["pick_rate"],
                "ban_rate": hero["ban_rate"],
                "matches": hero["matches"],
                "role": hero["role"],
                "tier": hero["tier"],
                "opponents": matchups,
                "maps": maps,
                "teamups": teamups_by_hero.get(norm_slug(hero["url_name"]), [])
            }

            # Пауза, чтобы не забанили
            time.sleep(random.uniform(1.5, 3.0))

        # 4. ВАЛИДАТОР ПЕРЕД СОХРАНЕНИЕМ
        # Не допускаем запись битого файла: если слишком много героев ВООБЩЕ
        # без данных (ни матчапов, ни карт) — это провал сбора, сохраняем в
        # .incomplete и прерываем, чтобы мусор не попал в базу.
        # Герои без карт, но с матчапами, — НЕ провал (сайт не даёт карты).
        total = len(heroes)
        failed = len(failed_heroes)
        logger.info(f"Собрано: {total - failed}/{total} героев с данными, полностью пустых: {failed}")
        if no_maps_heroes:
            logger.info(f"Герои без данных по картам (сайт не даёт, матчапы есть): {no_maps_heroes}")
        failure_ratio = (failed / total) if total else 1.0
        MAX_FAILURE_RATIO = 0.05  # допустимо <=5% полностью пустых героев

        if failed and failure_ratio > MAX_FAILURE_RATIO:
            incomplete_path = save_to_json(all_data, suffix="_INCOMPLETE")
            logger.error(
                f"ВАЛИДАЦИЯ ПРОВАЛЕНА: {failed}/{total} героев ({failure_ratio:.0%}) "
                f"ВООБЩЕ без данных. Превышен порог {MAX_FAILURE_RATIO:.0%}. "
                f"Битый файл НЕ записан как валидный, сохранён как: {incomplete_path}"
            )
            raise RuntimeError(
                f"Сбор данных неполный: {failed}/{total} героев совсем без данных. "
                f"См. лог выше: {failed_heroes}"
            )

        if failed:
            logger.warning(
                f"Допустимое число полностью пустых героев ({failed}), в пределах "
                f"порога {MAX_FAILURE_RATIO:.0%}. Проверь логи: {failed_heroes}"
            )

        saved_path = save_to_json(all_data)
        filename = os.path.basename(saved_path)
        write_latest_index(filename)
        logger.info("=== ГОТОВО ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка")
    finally:
        context.close()
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    main(season="9.0")