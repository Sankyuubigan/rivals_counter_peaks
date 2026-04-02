import json
import time
import logging
import random
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
    """Переходит по URL, игнорируя зависание на рекламе."""
    try:
        logger.info(f"Переход на {url}")
        # wait_until='commit' ждет только соединения, а не загрузки всей тяжелой рекламы
        page.goto(url, wait_until='commit', timeout=30000)
        
        # Небольшая пауза и скролл, чтобы инициировать загрузку контента
        time.sleep(1)
        page.evaluate("window.scrollTo(0, 300)")
        return True
    except Exception as e:
        logger.error(f"Ошибка перехода: {e}")
        return False

def get_teamups_data(page):
    """Получает данные о тим апах."""
    logger.info("--- Сбор Team-Ups ---")
    if not safe_goto(page, "https://rivalsmeta.com/tier-list/team-ups"):
        return []

    try:
        # Ждем именно контент
        page.wait_for_selector('.tier', timeout=15000)
        
        teamups_data = page.evaluate('''() => {
            const teamups = [];
            const tierBlocks = document.querySelectorAll('.tier');
            tierBlocks.forEach(tierBlock => {
                const tierName = tierBlock.querySelector('.t-name')?.textContent.trim() || 'Unknown';
                const contentElement = tierBlock.querySelector('.content.teamup');
                if (!contentElement) return;
                
                const teamupElements = contentElement.querySelectorAll(':scope > .teamup');
                teamupElements.forEach(teamupElement => {
                    const winRateElement = teamupElement.querySelector('.win-rate');
                    const teamupHeroesElement = teamupElement.querySelector('.teamup-heroes');
                    
                    if (!winRateElement || !teamupHeroesElement) return;
                    
                    const winRate = winRateElement.textContent.trim();
                    const heroes = Array.from(teamupElement.querySelectorAll('.teamup-heroes .cha img'))
                        .map(img => img.getAttribute('alt')?.trim())
                        .filter(name => name);
                    
                    if (heroes.length >= 2) {
                        teamups.push({ heroes, win_rate: winRate, tier: tierName });
                    }
                });
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
        
        heroes_data = page.evaluate('''() => {
            const heroes = [];
            const table = document.querySelector('table');
            if (!table) return heroes;
            
            const rows = table.querySelectorAll('tbody tr');
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const cells = row.querySelectorAll('td');
                
                if (cells.length >= 7) {
                    let heroName = cells[0].textContent.trim().replace(/\\s+/g, ' ').trim();
                    let urlName = heroName.toLowerCase().replace(/[^a-z0-9\\s-]/g, '').replace(/\\s+/g, '-').replace(/^-+|-+$/g, '');
                    
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

def get_matchups_and_maps(page, hero_url_name, season="1"):
    """Собирает матчапы и карты для одного героя."""
    
    # 1. MATCHUPS
    matchups = []
    url_matchups = f"https://rivalsmeta.com/characters/{hero_url_name}/matchups"
    if safe_goto(page, url_matchups):
        try:
            # Проверяем 404
            if "404" in page.title():
                logger.warning(f"Матчапы {hero_url_name} - 404")
            else:
                page.wait_for_selector('table', timeout=5000)
                matchups = page.evaluate('''() => {
                    const allMatchups = [];
                    const tables = document.querySelectorAll('table');
                    for (const table of tables) {
                        const headers = Array.from(table.querySelectorAll('th')).map(h => h.textContent.trim().toLowerCase());
                        if (headers.includes('hero') && headers.includes('win rate')) {
                            const rows = table.querySelectorAll('tbody tr');
                            for (const row of rows) {
                                const cells = row.querySelectorAll('td');
                                if (cells.length < 4) continue;
                                
                                let opponentName = cells[0].textContent.trim().replace(/^\\d+\\s*W\\s*/, '').replace(/\\s*VS.*$/, '');
                                if (!opponentName) {
                                    const img = cells[0].querySelector('img');
                                    if (img) opponentName = img.alt || '';
                                }
                                opponentName = opponentName.trim();
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
        except Exception:
            pass # Если не нашли таблицу, возвращаем пустой список

    time.sleep(1)

    # 2. MAPS
    maps_data = []
    url_maps = f"https://rivalsmeta.com/characters/{hero_url_name}/maps"
    if safe_goto(page, url_maps):
        try:
            if "404" in page.title():
                logger.warning(f"Карты {hero_url_name} - 404")
            else:
                page.wait_for_selector('table', timeout=5000)
                maps_data = page.evaluate('''() => {
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
                                    allMaps.push({
                                        map_name: nameEl.textContent.trim(),
                                        matches: cells[1].textContent.trim(),
                                        win_rate: cells[2].textContent.trim()
                                    });
                                }
                            }
                        }
                    }
                    return allMaps;
                }''')
        except Exception:
            pass

    return matchups, maps_data

def save_to_json(data):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"marvel_rivals_stats_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Сохранено в {filename}")

def main(season="1"):
    logger.info(f"=== ЗАПУСК СКРИПТА (СЕЗОН {season}) ===")
    
    playwright = sync_playwright().start()
    browser, context, page = init_browser(playwright)
    
    try:
        # 1. Тим апы
        teamups = get_teamups_data(page)
        time.sleep(2)
        
        # 2. Список героев
        heroes = get_heroes_list(page, season)
        
        if not heroes:
            logger.error("Герои не найдены. Выход.")
            return

        all_data = {'teamups': teamups, 'heroes': {}}
        
        # 3. Проход по каждому герою
        for i, hero in enumerate(heroes):
            logger.info(f"[{i+1}/{len(heroes)}] Обработка: {hero['display_name']}")
            
            matchups, maps = get_matchups_and_maps(page, hero["url_name"], season)
            
            all_data["heroes"][hero["display_name"]] = {
                "win_rate": hero["win_rate"],
                "pick_rate": hero["pick_rate"],
                "ban_rate": hero["ban_rate"],
                "matches": hero["matches"],
                "role": hero["role"],
                "tier": hero["tier"],
                "opponents": matchups,
                "maps": maps
            }
            
            # Пауза, чтобы не забанили
            time.sleep(random.uniform(1.5, 3.0))
            
        save_to_json(all_data)
        logger.info("=== ГОТОВО ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка")
    finally:
        context.close()
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    main(season="7.0")