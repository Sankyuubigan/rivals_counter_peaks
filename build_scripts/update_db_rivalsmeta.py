import json
import time
import logging
import random
import re
import os
import sys
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

def _season_version(label):
    """Достаёт номер версии из подписи сезона: 'Season 10.5' -> '10.5'."""
    match = re.search(r'(\d+(?:\.\d+)?)', label or '')
    return match.group(1) if match else None


def pick_latest_season(options):
    """Выбирает самый свежий сезон из списка option'ов сайта.

    options: список dict {'value': '21', 'label': 'Season 10.5'}.
    У сайта value — монотонный целый номер, поэтому максимум = свежий сезон
    (это надёжнее, чем брать последний <option> или полагаться на selected).

    Возвращает (version, label); (None, None), если разобрать нечего.
    """
    if not options:
        return None, None

    def rank(opt):
        value = str(opt.get('value', '')).strip()
        return int(value) if value.isdigit() else -1

    best = max(options, key=rank)
    label = (best.get('label') or '').strip()
    return _season_version(label), label


def detect_latest_season(page):
    """Определяет последний сезон на сайте. Возвращает версию ('10.5') или None."""
    if not safe_goto(page, "https://rivalsmeta.com/characters"):
        logger.error("Не удалось открыть /characters для определения сезона.")
        return None

    try:
        page.wait_for_selector('#season_filter', timeout=20000)
        options = page.evaluate('''() => Array.from(document.querySelectorAll('#season_filter option'))
            .map(o => ({ value: o.value || '', label: (o.textContent || '').trim(), selected: !!o.selected }))''')
    except Exception as e:
        logger.error(f"Не удалось прочитать список сезонов: {e}")
        return None

    version, label = pick_latest_season(options)
    if not version:
        logger.error(f"Не удалось определить версию сезона из {options}")
        return None

    marked = [o['label'] for o in options if o.get('selected')]
    logger.info(
        f"Последний сезон на сайте: {label!r} (версия {version}). "
        f"Помечен selected на сайте: {marked or '—'}."
    )
    if marked and marked[0].strip() != label:
        logger.warning(
            f"Похоже, свежий не всегда отмечен на сайте (selected={marked[0]!r}, "
            f"максимальный value={label!r}). Используем максимальный."
        )
    return version


def select_season(page, season, selector='#season_filter'):
    """Выбирает сезон в выпадающем списке по ТОЧНОМУ номеру версии.

    Сравнение строгое: '1' не должен цеплять 'Season 1.5' или 'Season 10'.
    """
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

    target = _season_version(str(season)) or str(season).strip()
    options = season_select.query_selector_all('option')
    season_value = None
    for option in options:
        if _season_version(option.text_content()) == target:
            season_value = option.get_attribute('value')
            break

    if season_value:
        season_select.select_option(value=season_value)
        logger.info(f"Сезон {season} выбран. Ждем обновления...")
        time.sleep(3)
        return True
    logger.warning(f"Сезон {season} не найден в списке на сайте.")
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

            const norm = s => (s || '').replace(/\s+/g, ' ').trim();

            // Колонки резолвим по ЗАГОЛОВКАМ, а не по жёстким индексам.
            // Сайт регулярно добавляет колонки (напр. "#" с номером),
            // и при фиксированных индексах всё молча съезжает на одну
            // ячейку: имя героя превращается в "1", slug — в "1",
            // и каждый запрос падает с 500.
            const headerText = Array.from(table.querySelectorAll('thead th')).map(th => {
                const clone = th.cloneNode(true);
                clone.querySelectorAll('svg, .info-tip, .tip-body, script').forEach(n => n.remove());
                return norm(clone.textContent).toLowerCase();
            });
            const findIdx = prefix => headerText.findIndex(h => h.startsWith(prefix));

            const idx = {
                hero:      findIdx('hero'),
                tier:      findIdx('tier'),
                win_rate:  findIdx('win rate'),
                pick_rate: findIdx('pick rate'),
                ban_rate:  findIdx('ban rate'),
                matches:   findIdx('matches'),
            };

            const required = ['hero', 'win_rate', 'pick_rate', 'ban_rate', 'matches'];
            if (required.some(k => idx[k] === -1)) {
                console.warn('[rivalsmeta] Не распознаны заголовки таблицы героев:', headerText);
                return heroes;
            }

            const rows = table.querySelectorAll('tbody tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length <= idx.matches) continue;

                const heroCell = cells[idx.hero];

                // Имя героя: сначала вложенный блок, потом текст ячейки.
                const nameEl = heroCell.querySelector('.meta .name') || heroCell.querySelector('.name');
                const heroName = norm(nameEl ? nameEl.textContent : heroCell.textContent);
                if (!heroName) continue;

                // Берём РЕАЛЬНЫЙ slug из ссылки на героя в таблице,
                // а не генерируем из имени. Сайт сам знает правильный
                // URL (например /characters/peni-parker), и генерация
                // из имени ломалась (давала "peniparker") -> 500 ошибка.
                let urlName = '';
                const heroLink = heroCell.querySelector('a[href*="/characters/"]');
                if (heroLink) {
                    const href = heroLink.getAttribute('href') || '';
                    const parts = href.split('/').filter(Boolean);
                    // последний сегмент пути и есть slug
                    urlName = parts[parts.length - 1] || '';
                }
                if (!urlName) {
                    // Fallback: генерация из имени, если ссылки нет
                    urlName = heroName.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/^-+|-+$/g, '');
                }

                let role = '';
                const roleImg = heroCell.querySelector('img.hero-class');
                if (roleImg) {
                    // Роль извлекаем из имени файла в src, т.к. alt содержит имя героя (баг сайта)
                    // Пример: /images/vanguard.png -> vanguard
                    const src = roleImg.getAttribute('src') || '';
                    const match = src.match(/\/images\/([a-z_-]+)\.png/i);
                    if (match) {
                        role = match[1].charAt(0).toUpperCase() + match[1].slice(1);
                    }
                }
                if (!role) role = heroCell.textContent.trim();

                const txt = key => norm(cells[idx[key]].textContent);

                heroes.push({
                    display_name: heroName,
                    url_name: urlName,
                    role: role,
                    tier: idx.tier !== -1 ? txt('tier') : '',
                    win_rate: txt('win_rate'),
                    pick_rate: txt('pick_rate'),
                    ban_rate: txt('ban_rate'),
                    matches: txt('matches'),
                });
            }
            return heroes;
        }''')

        valid_heroes = [h for h in heroes_data if h.get('display_name') and h['display_name'] != 'Hero']

        # Ловим съехавшую разметку ДО обхода героев, а не после 56 запросов
        # по несуществующим слагам вида /characters/1/matchups.
        SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')
        broken = [h for h in valid_heroes if not SLUG_RE.match(h.get('url_name') or '')]
        if broken:
            logger.error(
                "НЕВЕРНЫЕ slug'и — разметка сайта снова изменилась. "
                f"Примеры: {[(h['display_name'], h['url_name']) for h in broken[:5]]}"
            )
            return []

        logger.info(f"Найдено {len(valid_heroes)} героев. Первые 5: "
                    f"{[(h['display_name'], h['url_name']) for h in valid_heroes[:5]]}")
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


def extract_page_hero_name(page):
    """Достаёт имя героя с ОТКРЫТОЙ страницы героя.

    Приоритет: <h2 class="name"> в шапке героя, затем <h1> заголовок,
    затем <title>. Возвращает '' если ничего не нашли.
    """
    try:
        name = page.evaluate(r'''() => {
            const norm = s => (s || '').replace(/\s+/g, ' ').trim();

            const h2 = document.querySelector('h2.name');
            if (h2 && norm(h2.textContent)) return norm(h2.textContent);

            const h1 = document.querySelector('h1');
            if (h1) {
                const span = h1.querySelector('span');
                const text = norm(span ? span.textContent : h1.textContent);
                if (text) return text.replace(/\s+(Counters and Matchups|Best Maps|Overview|Maps|Matchups)$/i, '');
            }

            const title = norm(document.title);
            const m = title.match(/^Marvel Rivals\s+(.+?)\s+(Counters and Matchups|Best Maps|Overview|Maps|Matchups)$/i);
            return m ? norm(m[1]) : '';
        }''')
        return name or ''
    except Exception as e:
        logger.warning(f"Не удалось извлечь имя героя со страницы: {e}")
        return ''


def get_matchups_and_maps(page, hero_url_name, season="1"):
    """Собирает матчапы и карты для одного героя.

    Возвращает (matchups, maps_data, ok, hero_name_on_page).

    Имя героя берётся САМОЙ страницы героя (<h2 class="name">), а не из
    общей таблицы /characters: при смене сезона сайт перерисовывает
    список, и в момент чтения имя и href в строке иногда принадлежат
    разным героям ("Magik" -> gorr-the-god-butcher). Из-за этого в базу
    попадали матчапы ОДНОГО героя под именем ДРУГОГО. Slug при этом
    всегда корректный — мы по нему и переходим, поэтому он и остаётся
    единственным источником правды о том, чью страницу мы открыли.

    При 500/таймауте делает reload и повторяет попытки. Если после всех
    попыток данные не собраны — возвращает ok=False (вызывающий код обязан
    остановиться, НЕ записывая битый файл).
    """
    ok = True
    hero_name_on_page = ''

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
                # Достаём имя героя ОТКРЫТОЙ страницы — это достоверный
                # источник, в отличие от строки в общем списке.
                hero_name_on_page = extract_page_hero_name(page)
                matchups = page.evaluate(r'''() => {
                    const allMatchups = [];
                    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

                    // Как и в списке героев — колонки по заголовкам. Сайт
                    // добавил колонку "Matchup" (полоска W/L), из-за чего
                    // жёсткие cells[1..3] читали win_rate/difference/matches
                    // с ЗАДАННЫМ СДВИГОМ: в difference попадал win_rate,
                    // а по нему logic.js считает контрпики.
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headerText = Array.from(table.querySelectorAll('thead th')).map(th => {
                            const clone = th.cloneNode(true);
                            clone.querySelectorAll('svg, .info-tip, .tip-body, script').forEach(n => n.remove());
                            return norm(clone.textContent).toLowerCase();
                        });
                        const findIdx = prefix => headerText.findIndex(h => h.startsWith(prefix));

                        const idx = {
                            hero: findIdx('hero'),
                            win_rate: findIdx('win rate'),
                            difference: findIdx('difference'),
                            matches: findIdx('matches'),
                        };
                        if (idx.hero === -1 || idx.win_rate === -1) continue;

                        const rows = table.querySelectorAll('tbody tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length <= idx.win_rate) continue;

                            const heroCell = cells[idx.hero];

                            let opponentName = '';

                            // Текущая разметка: <a class="mu-hero"><img alt="Deadpool (Vanguard)">
                            const muHero = heroCell.querySelector('a.mu-hero');
                            if (muHero) {
                                const img = muHero.querySelector('img');
                                opponentName = (img ? img.getAttribute('alt') : '') || '';
                                if (!opponentName) {
                                    const nameEl = muHero.querySelector('.mu-name');
                                    if (nameEl) opponentName = nameEl.textContent || '';
                                }
                            }

                            // Старая разметка: .matchup > .cha, где первая
                            // не-.active сторона — это оппонент.
                            if (!opponentName) {
                                const matchupEl = heroCell.querySelector('.matchup');
                                if (matchupEl) {
                                    const chaEls = matchupEl.querySelectorAll('.cha');
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
                            }
                            if (!opponentName) {
                                const img = heroCell.querySelector('img');
                                if (img) opponentName = img.getAttribute('alt') || '';
                            }
                            opponentName = norm(opponentName);
                            if (!opponentName) continue;

                            allMatchups.push({
                                opponent: opponentName,
                                win_rate: norm(cells[idx.win_rate].textContent),
                                difference: idx.difference !== -1 ? norm(cells[idx.difference].textContent) : '',
                                matches: idx.matches !== -1 ? norm(cells[idx.matches].textContent) : '',
                            });
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
                    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

                    // Колонки по заголовкам + поиск картинки карты без
                    // привязки к обёртке ".image" (её на сайте больше нет,
                    // из-за чего map_name приходил пустым для ВСЕХ карт).
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headerText = Array.from(table.querySelectorAll('thead th')).map(th => {
                            const clone = th.cloneNode(true);
                            clone.querySelectorAll('svg, .info-tip, .tip-body, script').forEach(n => n.remove());
                            return norm(clone.textContent).toLowerCase();
                        });
                        const findIdx = prefix => headerText.findIndex(h => h.startsWith(prefix));

                        const idx = {
                            map: findIdx('map'),
                            matches: findIdx('matches'),
                            win_rate: findIdx('win rate'),
                        };
                        if (idx.map === -1) continue;

                        const rows = table.querySelectorAll('tbody tr');
                        for (const row of rows) {
                            const cells = row.querySelectorAll('td');
                            if (cells.length <= idx.map) continue;

                            const mapImg = cells[idx.map].querySelector('img');
                            const imgSrc = mapImg ? (mapImg.getAttribute('src') || '') : '';
                            // Извлекаем img_map_xxx из src
                            const match = imgSrc.match(/images\/Map\/(img_map_\w+)\.png/);
                            const mapFilename = match ? match[1] : '';
                            // Мусорные записи с пустым map_name не пишем:
                            // logic.js потом не сможет сопоставить карту с именем.
                            if (!mapFilename) continue;

                            allMaps.push({
                                map_name: mapFilename,
                                matches: idx.matches !== -1 ? norm(cells[idx.matches].textContent) : '',
                                win_rate: idx.win_rate !== -1 ? norm(cells[idx.win_rate].textContent) : '',
                            });
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
    return matchups, maps_data, ok, hero_name_on_page

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

def build_meta(season):
    """Метаданные базы: сезон + когда собрана. Кладутся первым ключом в JSON."""
    now = time.localtime()
    # %Z на Windows отдаёт мусор вида "RTZ 2 (мин)", поэтому берём %z
    # и приводим к читаемому виду +03:00.
    offset = time.strftime("%z", now)
    if len(offset) == 5 and offset[0] in "+-":
        offset = f"{offset[:3]}:{offset[3:]}"
    return {
        "season": str(season),
        "season_label": f"Season {season}",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", now),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "utc_offset": offset,
        "source": "https://rivalsmeta.com",
        "scraper": os.path.basename(__file__),
    }


def main(season="auto"):
    logger.info("=== ЗАПУСК СКРИПТА ===")

    playwright = sync_playwright().start()
    browser, context, page = init_browser(playwright)

    try:
        # 0. Сезон. По умолчанию берём самый свежий на сайте, чтобы не
        #    вписывать его руками каждый раз. Конкретную версию всё ещё
        #    можно передать аргументом: main(season="9.5").
        if not season or str(season).lower() == "auto":
            season = detect_latest_season(page)
            if not season:
                logger.error("Не удалось определить последний сезон. Выход.")
                return
            logger.info(f"Автоматически выбран последний сезон: {season}")
        logger.info(f"Работаем с сезоном: {season}")

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

        # meta идёт ПЕРВЫМ ключом — по нему сразу видно, какой сезон и
        # когда собрана база. Приложение читает только 'heroes'/'teamups',
        # лишний ключ ему не мешает (desktop.js проверяет их наличие).
        all_data = {'meta': build_meta(season), 'teamups': teamups, 'heroes': {}}
        failed_heroes = []   # герои, по которым НЕ собрано ВООБЩЕ ничего (провал)
        no_maps_heroes = []  # герои, у которых нет карт, но есть матчапы (ок, сайт не даёт)

        # 3. Проход по каждому герою
        for i, hero in enumerate(heroes):
            logger.info(f"[{i+1}/{len(heroes)}] Обработка: {hero['display_name']} ({hero['url_name']})")

            matchups, maps, ok, hero_name_on_page = get_matchups_and_maps(page, hero["url_name"], season)

            # Ключ в базе — имя с ОТКРЫТОЙ страницы героя. Имя из общего
            # списка /characters в момент чтения может принадлежать другой
            # строке, чем href, и тогда матчапы одного героя записались бы
            # под именем другого. Slag всегда точен, страница — источник
            # правды, поэтому сверяем и предупреждаем, если они разошлись.
            hero_name = hero_name_on_page or hero['display_name']
            if hero_name_on_page and hero_name_on_page != hero['display_name']:
                logger.warning(
                    f"Имя из списка и имя страницы разошлись: "
                    f"список='{hero['display_name']}' -> страница='{hero_name_on_page}' "
                    f"(slug='{hero['url_name']}'). Используем имя страницы."
                )

            # Провал только если вообще ничего не собрано (ни матчапов, ни карт).
            # Отсутствие карт при наличии матчапов — допустимо (сайт не даёт
            # данные по картам для некоторых героев), алгоритм это переварит.
            has_data = bool(matchups) or bool(maps)
            if not has_data:
                failed_heroes.append(hero_name)
                logger.error(
                    f"ДАННЫЕ НЕ СОБРАНЫ для {hero_name} "
                    f"(matchups={len(matchups)}, maps={len(maps)})"
                )
            elif not maps:
                no_maps_heroes.append(hero_name)

            all_data["heroes"][hero_name] = {
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

        # Проверка атрибуции данных: сайт ИСКЛЮЧАЕТ зеркальные матчапы,
        # поэтому герой не должен встречаться в списке СВОИХ оппонентов.
        # Если встречается — значит матчапы собраны со страницы другого
        # героя и записаны не под тем именем.
        mismatched = []
        for hero_name, payload in all_data["heroes"].items():
            target = hero_name.lower().strip()
            for opp in payload.get("opponents") or []:
                if (opp.get("opponent") or "").lower().strip() == target:
                    mismatched.append(hero_name)
                    break
        if mismatched:
            logger.error(
                f"НАРУШЕНА АТРИБУЦИЯ: {len(mismatched)} героев встречаются "
                f"в списке своих оппонентов (данные со страниц других героев): "
                f"{mismatched[:10]}"
            )
            save_to_json(all_data, suffix="_INCOMPLETE")
            raise RuntimeError(
                f"Данные приписаны не тем героям ({len(mismatched)} шт.): {mismatched[:10]}"
            )

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

        all_data["meta"].update({
            "heroes_count": len(all_data["heroes"]),
            "heroes_with_matchups": sum(1 for h in all_data["heroes"].values() if h.get("opponents")),
            "heroes_with_maps": sum(1 for h in all_data["heroes"].values() if h.get("maps")),
            "heroes_failed": failed,
            "teamups_count": len(teamups),
        })
        logger.info(f"Метаданные базы: {all_data['meta']}")

        saved_path = save_to_json(all_data)
        filename = os.path.basename(saved_path)
        write_latest_index(filename)
        logger.info("=== ГОТОВО ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка")
    finally:
        # Очистку оборачиваем в try/except: если драйвер Playwright уже
        # отвалился, необработанное исключение из close() перебивает и
        # маскирует настоящую ошибку сбора ("Connection closed while
        # reading from the driver" вместо текста валидатора).
        try:
            context.close()
        except Exception as e:
            logger.warning(f"Не удалось закрыть контекст: {e}")
        try:
            browser.close()
        except Exception as e:
            logger.warning(f"Не удалось закрыть браузер: {e}")
        try:
            playwright.stop()
        except Exception as e:
            logger.warning(f"Не удалось остановить playwright: {e}")

if __name__ == "__main__":
    # По умолчанию season="auto" — скрипт сам находит последний сезон на
    # сайте. Конкретный можно задать так:
    #     python update_db_rivalsmeta.py 9.5
    season_arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    main(season=season_arg)