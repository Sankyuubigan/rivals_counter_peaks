import json
import time
import logging
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

def _create_page():
    """Создает и настраивает экземпляр страницы Playwright."""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1200, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    page = context.new_page()
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(45000)
    return page, context, browser, playwright

def get_heroes_list(season="1", max_retries=3):
    """Получает список всех героев со страницы characters с их глобальными статистиками."""
    logger.info(f"=== НАЧАЛО ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ (СЕЗОН {season}) ===")
    logger.info("Открываем страницу https://rivalsmeta.com/characters")
    
    page, context, browser, playwright = _create_page()
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            logger.info(f"Попытка {retry_count + 1} из {max_retries}")
            
            response = page.goto(
                "https://rivalsmeta.com/characters", 
                timeout=45000, 
                wait_until="domcontentloaded"
            )
            
            if response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                retry_count += 1
                continue
                
            time.sleep(3)
            
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
                    logger.info(f"Сезон {season} выбран.")
                    time.sleep(5)
            
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
                        const roleImg = cells[1].querySelector('img');
                        if (roleImg) role = roleImg.alt || roleImg.title || '';
                        if (!role) role = cells[1].textContent.trim();
                        if (!role || role === heroName) role = 'Unknown';
                        
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
            logger.info(f"Найдено {len(valid_heroes)} валидных героев.")
            
            context.close()
            browser.close()
            playwright.stop()
            logger.info("=== ЗАВЕРШЕНИЕ ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ ===")
            return valid_heroes
            
        except Exception as e:
            logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5)
    
    logger.error(f"Не удалось загрузить страницу после {max_retries} попыток")
    context.close()
    browser.close()
    playwright.stop()
    return []

def get_teamups_data(max_retries=3):
    """Получает данные о тим апах со страницы tier-list/team-ups."""
    logger.info("=== НАЧАЛО ПОЛУЧЕНИЯ ДАННЫХ О ТИМ АПАХ ===")
    
    page, context, browser, playwright = _create_page()
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = page.goto("https://rivalsmeta.com/tier-list/team-ups", timeout=45000, wait_until="domcontentloaded")
            if response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                retry_count += 1
                continue
                
            time.sleep(5)
            
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
            
            logger.info(f"Извлечено {len(teamups_data)} записей о тим апах.")
            context.close()
            browser.close()
            playwright.stop()
            logger.info("=== ЗАВЕРШЕНИЕ ПОЛУЧЕНИЯ ДАННЫХ О ТИМ АПАХ ===")
            return teamups_data
            
        except Exception as e:
            logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5)

    logger.error(f"Не удалось загрузить страницу тим апов после {max_retries} попыток")
    context.close()
    browser.close()
    playwright.stop()
    return []

def get_matchups_data(hero_url_name, season="1", max_retries=3):
    """Получает данные матчапов для конкретного героя."""
    url = f"https://rivalsmeta.com/characters/{hero_url_name}/matchups"
    logger.info(f"Загружаем матчапы для {hero_url_name}...")
    
    page, context, browser, playwright = _create_page()
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = page.goto(url, timeout=45000, wait_until="domcontentloaded")
            if response and response.status == 404:
                logger.warning(f"Страница матчапов не найдена для {hero_url_name} (404)")
                return []
            if response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                retry_count += 1
                continue
                
            time.sleep(3)
            
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
                            
                            let opponentName = cells[0].textContent.trim()
                                .replace(/^\\d+\\s*W\\s*/, '').replace(/\\s*VS.*$/, '');
                            
                            if (!opponentName) {
                                const img = cells[0].querySelector('img');
                                if (img) opponentName = img.alt || img.src.match(/\\/([^\\/]+)\\/img_heroportrait/)?.[1]?.replace(/-/g, ' ') || '';
                            }
                            
                            opponentName = opponentName.replace(/\\s+/g, ' ').replace(/[^a-zA-Z\\s&]/g, '').trim();
                            if (opponentName) opponentName = opponentName.charAt(0).toUpperCase() + opponentName.slice(1);
                            if (!opponentName) opponentName = 'Unknown Hero';
                            
                            allMatchups.push({
                                opponent: opponentName,
                                win_rate: cells[1].textContent.trim(),
                                difference: cells[2].textContent.trim(),
                                matches: cells[3].textContent.trim()
                            });
                        }
                    }
                }
                return allMatchups;
            }''')
            
            logger.info(f"Найдено {len(matchups)} матчапов для {hero_url_name}.")
            context.close()
            browser.close()
            playwright.stop()
            return matchups
            
        except Exception as e:
            logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(5)

    logger.error(f"Не удалось загрузить страницу матчапов для {hero_url_name} после {max_retries} попыток")
    context.close()
    browser.close()
    playwright.stop()
    return []

# --- НОВАЯ ФУНКЦИЯ ---
def get_maps_data(hero_url_name, max_retries=3):
    """Получает статистику по картам для конкретного героя."""
    url = f"https://rivalsmeta.com/characters/{hero_url_name}/maps"
    logger.info(f"Загружаем статистику по картам для {hero_url_name} с {url}")
    
    page, context, browser, playwright = _create_page()

    retry_count = 0
    while retry_count < max_retries:
        try:
            logger.info(f"Попытка {retry_count + 1} из {max_retries}")
            
            response = page.goto(
                url, 
                timeout=45000, 
                wait_until="domcontentloaded"
            )
            
            if response and response.status == 404:
                logger.warning(f"Страница с картами не найдена для {hero_url_name} (404)")
                return []
            if response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                retry_count += 1
                continue
            
            # Даем секунду на отрисовку, т.к. больше не ждем
            time.sleep(1)

            # ИЗМЕНЕННЫЙ JavaScript, который соответствует реальной структуре HTML
            maps_stats = page.evaluate('''() => {
                const allMaps = [];
                // Ищем таблицы по их классу для точности
                const tables = document.querySelectorAll('table.characters-table');

                for (const table of tables) {
                    const headers = table.querySelectorAll('th');
                    let hasMapHeader = false;
                    let hasMatchesHeader = false;
                    let hasWinRateHeader = false;

                    // Проверяем, что у таблицы нужные заголовки
                    for (const header of headers) {
                        const headerText = header.textContent.trim().toLowerCase();
                        if (headerText === 'map') hasMapHeader = true;
                        if (headerText === 'matches') hasMatchesHeader = true;
                        if (headerText === 'win rate') hasWinRateHeader = true;
                    }

                    if (hasMapHeader && hasMatchesHeader && hasWinRateHeader) {
                        const rows = table.querySelectorAll('tbody tr');
                        for (const row of rows) {
                            // Ищем название карты в нужном div
                            const nameElement = row.querySelector('td .name');
                            const cells = row.querySelectorAll('td');

                            // Убеждаемся, что нашли название и есть 3 колонки данных
                            if (nameElement && cells.length >= 3) {
                                allMaps.push({
                                    map_name: nameElement.textContent.trim(),
                                    matches: cells[1].textContent.trim(),
                                    win_rate: cells[2].textContent.trim()
                                });
                            }
                        }
                    }
                }
                return allMaps;
            }''')
            
            logger.info(f"Извлечено {len(maps_stats)} записей по картам.")
            
            context.close()
            browser.close()
            playwright.stop()
            return maps_stats
            
        except Exception as e:
            logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Ждем 5 секунд перед повторной попыткой...")
                time.sleep(5)
            continue
        
    logger.error(f"Не удалось загрузить страницу карт для {hero_url_name} после {max_retries} попыток")
    context.close()
    browser.close()
    playwright.stop()
    return []


def save_to_json(data, filename=None):
    """Сохраняет данные в JSON с временной меткой."""
    if not filename:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"marvel_rivals_stats_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные успешно сохранены в {filename}")
        return filename
    except Exception as e:
        logger.exception("Ошибка при сохранении данных в JSON")
        return None

def main(season="1"):
    """Основная функция."""
    logger.info(f"=== НАЧАЛО РАБОТЫ СКРИПТА (СЕЗОН {season}) ===")
    
    try:
        teamups = get_teamups_data()
        heroes = get_heroes_list(season)
        
        if not heroes:
            logger.error("Не удалось получить список героев. Завершение работы.")
            return
        
        logger.info(f"Обнаружено {len(heroes)} героев для обработки.")
        
        all_data = {
            'teamups': teamups,
            'heroes': {}
        }
        
        for i, hero in enumerate(heroes):
            logger.info(f"--- Обработка героя {i+1}/{len(heroes)}: {hero['display_name']} ---")
            
            try:
                # Получаем матчапы
                matchups = get_matchups_data(hero["url_name"], season)
                
                # --- ВЫЗОВ НОВОЙ ФУНКЦИИ ---
                # Получаем статистику по картам
                maps = get_maps_data(hero["url_name"])

                hero_data = {
                    "win_rate": hero["win_rate"],
                    "pick_rate": hero["pick_rate"],
                    "ban_rate": hero["ban_rate"],
                    "matches": hero["matches"],
                    "role": hero["role"],
                    "tier": hero["tier"],
                    "opponents": matchups if matchups else [],
                    "maps": maps if maps else []  # --- ДОБАВЛЕНИЕ НОВЫХ ДАННЫХ В JSON ---
                }
                
                all_data["heroes"][hero["display_name"]] = hero_data
                logger.info(f"Успешно обработан {hero['display_name']}.")
                
                if i < len(heroes) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.exception(f"Ошибка при обработке {hero['display_name']}")
                continue
        
        if all_data["heroes"]:
            save_to_json(all_data)
            logger.info(f"Успешно обработано {len(all_data['heroes'])}/{len(heroes)} героев.")
        else:
            logger.warning("Не удалось собрать данные ни по одному герою.")
        
        logger.info("=== ЗАВЕРШЕНИЕ РАБОТЫ СКРИПТА ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка в основном процессе")
        raise

if __name__ == "__main__":
    main(season="4.5")