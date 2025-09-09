import json
import time
import re
import logging
from pathlib import Path
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

def block_unnecessary_resources(page):
    """Блокирует загрузку ненужных ресурсов для ускорения загрузки страницы"""
    blocked_resources = ['image', 'font', 'media']
    
    def block_route(route):
        resource_type = route.request.resource_type
        if resource_type in blocked_resources:
            route.abort()
        else:
            route.continue_()
    
    page.route('**', block_route)

def get_heroes_list(season="1", max_retries=3):
    """Получает список всех героев со страницы characters с их глобальными статистиками"""
    logger.info(f"=== НАЧАЛО ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ (СЕЗОН {season}) ===")
    logger.info("Открываем страницу https://rivalsmeta.com/characters")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
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
        
        # Устанавливаем таймауты
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(45000)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"Попытка {retry_count + 1} из {max_retries}")
                
                # Переходим на страницу
                logger.info("Загружаем страницу...")
                start_time = time.time()
                
                response = page.goto(
                    "https://rivalsmeta.com/characters", 
                    timeout=45000, 
                    wait_until="domcontentloaded"
                )
                
                # Проверяем статус ответа
                if response and response.status != 200:
                    logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                    retry_count += 1
                    continue
                    
                load_time = time.time() - start_time
                logger.info(f"Страница загружена за {load_time:.2f} секунд")
                
                # Даем время на инициализацию JavaScript
                time.sleep(3)
                
                # Пробуем выбрать сезон через select
                logger.info(f"Пробуем выбрать сезон {season} через select...")
                
                season_select = page.query_selector('#season_filter')
                if season_select:
                    logger.info("Найден select с id season_filter")
                    
                    options = season_select.query_selector_all('option')
                    logger.info(f"Доступные опции сезона: {[option.text_content() for option in options]}")
                    
                    season_value = None
                    for option in options:
                        option_text = option.text_content().strip()
                        if season in option_text:
                            season_value = option.get_attribute('value')
                            logger.info(f"Найдена опция '{option_text}' со значением '{season_value}'")
                            break
                    
                    if season_value:
                        season_select.select_option(value=season_value)
                        logger.info(f"Сезон {season} выбран через select_option")
                        time.sleep(5)  # Ждем загрузки данных после выбора сезона
                    else:
                        logger.warning(f"Не найдена опция для сезона {season}")
                else:
                    logger.warning("Не найден select с id season_filter")
                
                # Ждем загрузки данных
                logger.info("Ждем загрузки данных...")
                time.sleep(3)
                
                # Извлекаем данные через JavaScript
                heroes_data = page.evaluate('''() => {
                    const heroes = [];
                    const table = document.querySelector('table');
                    if (!table) return heroes;
                    
                    const rows = table.querySelectorAll('tbody tr');
                    for (let i = 0; i < rows.length; i++) {
                        const row = rows[i];
                        const cells = row.querySelectorAll('td');
                        
                        if (cells.length >= 7) {
                            // Извлекаем имя героя из первой ячейки
                            let heroName = cells[0].textContent.trim();
                            heroName = heroName.replace(/\\s+/g, ' ').trim();
                            
                            // Формируем URL-friendly версию
                            let urlName = heroName.toLowerCase()
                                .replace(/[^a-z0-9\\s-]/g, '')
                                .replace(/\\s+/g, '-')
                                .replace(/^-+|-+$/g, '');
                                
                            // Пытаемся извлечь роль
                            let role = '';
                            const roleCell = cells[1];
                            const roleImg = roleCell.querySelector('img');
                            if (roleImg) {
                                if (roleImg.alt) {
                                    role = roleImg.alt.trim();
                                } else if (roleImg.title) {
                                    role = roleImg.title.trim();
                                }
                            } else {
                                role = roleCell.textContent.trim();
                            }
                            
                            // Если роль не найдена, устанавливаем значение по умолчанию
                            if (!role || role === heroName) {
                                role = 'Unknown';
                            }
                            
                            // Извлекаем глобальные статистики
                            const tier = cells[2].textContent.trim();
                            const winRate = cells[3].textContent.trim();
                            const pickRate = cells[4].textContent.trim();
                            const banRate = cells[5].textContent.trim();
                            const matches = cells[6].textContent.trim();
                            
                            heroes.push({
                                display_name: heroName,
                                url_name: urlName,
                                role: role,
                                tier: tier,
                                win_rate: winRate,
                                pick_rate: pickRate,
                                ban_rate: banRate,
                                matches: matches,
                                row_index: i
                            });
                        }
                    }
                    return heroes;
                }''')
                
                logger.info(f"Найдено {len(heroes_data)} потенциальных героев через JS-метод")
                
                # Фильтруем пустые и дубликаты
                valid_heroes = []
                seen_urls = set()
                
                for hero in heroes_data:
                    if not hero['display_name'] or hero['display_name'] == 'Hero':
                        continue
                    
                    if hero['url_name'] in seen_urls:
                        continue
                        
                    seen_urls.add(hero['url_name'])
                    valid_heroes.append(hero)
                
                logger.info(f"Отфильтровано до {len(valid_heroes)} валидных героев")
                
                context.close()
                browser.close()
                logger.info("=== ЗАВЕРШЕНИЕ ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ ===")
                return valid_heroes
                
            except Exception as e:
                logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ждем 5 секунд перед повторной попыткой...")
                    time.sleep(5)
                continue
        
        logger.error(f"Не удалось загрузить страницу после {max_retries} попыток")
        context.close()
        browser.close()
        return []

def get_teamups_data(max_retries=3):
    """Получает данные о тим апах со страницы tier-list/team-ups"""
    logger.info("=== НАЧАЛО ПОЛУЧЕНИЯ ДАННЫХ О ТИМ АПАХ ===")
    logger.info("Открываем страницу https://rivalsmeta.com/tier-list/team-ups")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
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
        
        # НЕ блокируем ресурсы, так как нам нужны изображения для извлечения имен героев
        # block_unnecessary_resources(page)
        
        # Устанавливаем таймауты
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(45000)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"Попытка {retry_count + 1} из {max_retries}")
                
                # Переходим на страницу
                logger.info("Загружаем страницу тим апов...")
                start_time = time.time()
                
                response = page.goto(
                    "https://rivalsmeta.com/tier-list/team-ups", 
                    timeout=45000, 
                    wait_until="domcontentloaded"
                )
                
                # Проверяем статус
                if response and response.status != 200:
                    logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                    retry_count += 1
                    continue
                    
                load_time = time.time() - start_time
                logger.info(f"Страница загружена за {load_time:.2f} секунд")
                
                # Даем время на загрузку динамических данных
                logger.info("Ожидаем загрузки данных тим апов...")
                time.sleep(5)
                
                # Извлекаем данные тим апов через JavaScript, анализируя HTML-структуру
                teamups_data = page.evaluate('''() => {
                    const teamups = [];
                    
                    // Ищем все tier блоки (S, A, B, C)
                    const tierBlocks = document.querySelectorAll('.tier');
                    
                    tierBlocks.forEach(tierBlock => {
                        // Получаем название tier (S, A, B, C)
                        const tierNameElement = tierBlock.querySelector('.t-name');
                        const tierName = tierNameElement ? tierNameElement.textContent.trim() : 'Unknown';
                        
                        // Ищем все тим апы внутри этого tier, но только те, которые имеют структуру тимапа
                        // Используем более точный селектор: ищем .teamup внутри .content.teamup
                        const contentElement = tierBlock.querySelector('.content.teamup');
                        if (!contentElement) return;
                        
                        const teamupElements = contentElement.querySelectorAll(':scope > .teamup');
                        
                        teamupElements.forEach(teamupElement => {
                            // Проверяем, что это не общий контейнер, а конкретный тимап
                            // У тимапа должен быть .win-rate и .teamup-heroes
                            const winRateElement = teamupElement.querySelector('.win-rate');
                            const teamupHeroesElement = teamupElement.querySelector('.teamup-heroes');
                            
                            if (!winRateElement || !teamupHeroesElement) {
                                return; // Пропускаем, если структура не соответствует тимапу
                            }
                            
                            const winRate = winRateElement.textContent.trim();
                            
                            // Получаем имена героев
                            const heroElements = teamupElement.querySelectorAll('.teamup-heroes .cha img');
                            const heroes = [];
                            
                            heroElements.forEach(img => {
                                // Извлекаем имя героя из атрибута alt
                                const heroName = img.getAttribute('alt');
                                if (heroName && heroName.trim() !== '') {
                                    heroes.push(heroName.trim());
                                }
                            });
                            
                            // Если нашли хотя бы двух героев, добавляем тим ап
                            if (heroes.length >= 2) {
                                teamups.push({
                                    heroes: heroes,
                                    win_rate: winRate,
                                    tier: tierName
                                });
                            }
                        });
                    });
                    
                    return teamups;
                }''')
                
                logger.info(f"Извлечено {len(teamups_data)} записей о тим апах")
                
                if teamups_data:
                    logger.info("Примеры извлеченных тим апов:")
                    for i, teamup in enumerate(teamups_data[:5]):
                        logger.info(f"  {i+1}. {teamup['heroes']}: Win Rate={teamup['win_rate']}, Tier={teamup['tier']}")
                else:
                    logger.warning("Не удалось извлечь данные о тим апах")
                
                context.close()
                browser.close()
                logger.info("=== ЗАВЕРШЕНИЕ ПОЛУЧЕНИЯ ДАННЫХ О ТИМ АПАХ ===")
                return teamups_data
                
            except Exception as e:
                logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ждем 5 секунд перед повторной попыткой...")
                    time.sleep(5)
                continue
        
        logger.error(f"Не удалось загрузить страницу тим апов после {max_retries} попыток")
        context.close()
        browser.close()
        return []

def get_matchups_data(hero_url_name, season="1", max_retries=3):
    """Получает данные матчапов для конкретного героя"""
    url = f"https://rivalsmeta.com/characters/{hero_url_name}/matchups"
    logger.info(f"=== НАЧАЛО ОБРАБОТКИ ГЕРОЯ: {hero_url_name.upper()} ===")
    logger.info(f"Загружаем данные матчапов по URL: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
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
        
        # Блокируем ненужные ресурсы
        block_unnecessary_resources(page)
        
        # Устанавливаем таймауты
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(45000)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"Попытка {retry_count + 1} из {max_retries}")
                
                # Переходим на страницу
                logger.info("Загружаем страницу матчапов...")
                start_time = time.time()
                
                response = page.goto(
                    url, 
                    timeout=45000, 
                    wait_until="domcontentloaded"
                )
                
                # Проверяем статус
                if response and response.status == 404:
                    logger.warning(f"Страница матчапов не найдена для {hero_url_name} (404)")
                    context.close()
                    browser.close()
                    return []
                elif response and response.status != 200:
                    logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                    retry_count += 1
                    continue
                    
                load_time = time.time() - start_time
                logger.info(f"Страница загружена за {load_time:.2f} секунд")
                
                # Даем время на инициализацию JavaScript
                time.sleep(3)
                
                # Извлекаем данные матчапов
                matchups = page.evaluate('''() => {
                    const allMatchups = [];
                    const tables = document.querySelectorAll('table');
                    
                    for (const table of tables) {
                        const headers = table.querySelectorAll('th');
                        if (headers.length < 4) continue;
                        
                        const headerTexts = Array.from(headers).map(h => 
                            h.textContent.trim().toLowerCase()
                        );
                        
                        const hasHero = headerTexts.some(text => text.includes('hero'));
                        const hasWinRate = headerTexts.some(text => text.includes('win rate'));
                        const hasDifference = headerTexts.some(text => text.includes('difference'));
                        const hasMatches = headerTexts.some(text => text.includes('matches'));
                        
                        if (hasHero && hasWinRate && hasDifference && hasMatches) {
                            const rows = table.querySelectorAll('tbody tr');
                            for (const row of rows) {
                                const cells = row.querySelectorAll('td');
                                if (cells.length < 4) continue;
                                
                                let opponentName = '';
                                let cellText = cells[0].textContent.trim();
                                
                                cellText = cellText.replace(/^\\d+\\s*W\\s*/, '');
                                cellText = cellText.replace(/\\s*VS.*$/, '');
                                
                                if (cellText.trim() !== '') {
                                    opponentName = cellText.trim();
                                }
                                
                                if (!opponentName) {
                                    const img = cells[0].querySelector('img');
                                    if (img && img.alt) {
                                        opponentName = img.alt;
                                    }
                                }
                                
                                if (!opponentName) {
                                    const img = cells[0].querySelector('img');
                                    if (img && img.src) {
                                        const match = img.src.match(/\\/([^\\/]+)\\/img_heroportrait/);
                                        if (match && match[1]) {
                                            opponentName = match[1].replace(/-/g, ' ');
                                        }
                                    }
                                }
                                
                                if (!opponentName) {
                                    opponentName = 'Unknown Hero';
                                }
                                
                                opponentName = opponentName
                                    .replace(/\\s+/g, ' ')
                                    .trim()
                                    .replace(/[^a-zA-Z\\s&]/g, '')
                                    .replace(/\\s+/g, ' ')
                                    .trim();
                                
                                if (opponentName.length > 0) {
                                    opponentName = opponentName.charAt(0).toUpperCase() + opponentName.slice(1);
                                }
                                
                                const winRate = cells[1].textContent.trim();
                                const difference = cells[2].textContent.trim();
                                const matches = cells[3].textContent.trim();
                                
                                allMatchups.push({
                                    opponent: opponentName,
                                    win_rate: winRate,
                                    difference: difference,
                                    matches: matches
                                });
                            }
                        }
                    }
                    return allMatchups;
                }''')
                
                logger.info(f"Извлечено {len(matchups)} записей матчапов из всех таблиц")
                
                context.close()
                browser.close()
                logger.info("=== ЗАВЕРШЕНИЕ ОБРАБОТКИ ГЕРОЯ ===")
                return matchups
                
            except Exception as e:
                logger.error(f"Ошибка при попытке {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Ждем 5 секунд перед повторной попыткой...")
                    time.sleep(5)
                continue
        
        logger.error(f"Не удалось загрузить страницу матчапов после {max_retries} попыток")
        context.close()
        browser.close()
        return []

def save_to_json(data, filename=None):
    """Сохраняет данные в JSON с временной меткой"""
    if not filename:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"marvel_rivals_stats_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные успешно сохранены в {filename}")
        
        total_heroes = len(data.get('heroes', {}))
        total_matchups = sum(len(hero_data.get('opponents', [])) for hero_data in data.get('heroes', {}).values())
        total_teamups = len(data.get('teamups', []))
        logger.info(f"Статистика сохранения: {total_heroes} героев, {total_matchups} матчапов, {total_teamups} тим апов")
        
        return filename
    except Exception as e:
        logger.exception("Ошибка при сохранении данных в JSON")
        return None

def main(season="1"):
    """Основная функция"""
    logger.info(f"=== НАЧАЛО РАБОТЫ СКРИПТА (СЕЗОН {season}) ===")
    
    try:
        # Получаем данные о тим апах
        logger.info("Получаем данные о тим апах...")
        teamups = get_teamups_data()
        
        # Получаем список героев
        heroes = get_heroes_list(season)
        
        if not heroes:
            logger.error("Не удалось получить список героев. Завершение работы.")
            return
        
        logger.info(f"Обнаружено {len(heroes)} героев для обработки")
        
        all_data = {
            'teamups': teamups,
            'heroes': {}
        }
        
        for i, hero in enumerate(heroes):
            logger.info(f"--- Обработка героя {i+1}/{len(heroes)} ---")
            logger.info(f"Герой: {hero['display_name']} (URL: {hero['url_name']})")
            
            try:
                start_time = time.time()
                matchups = get_matchups_data(hero["url_name"], season)
                processing_time = time.time() - start_time
                
                hero_data = {
                    "win_rate": hero["win_rate"],
                    "pick_rate": hero["pick_rate"],
                    "ban_rate": hero["ban_rate"],
                    "matches": hero["matches"],
                    "role": hero["role"],
                    "tier": hero["tier"],
                    "opponents": matchups if matchups else []
                }
                
                all_data["heroes"][hero["display_name"]] = hero_data
                
                logger.info(f"Успешно обработан {hero['display_name']} за {processing_time:.2f} сек")
                logger.info(f"  Глобальная статистика: WR={hero['win_rate']}, PR={hero['pick_rate']}, BR={hero['ban_rate']}, M={hero['matches']}, Role={hero['role']}")
                
                if i < len(heroes) - 1:
                    logger.info(f"Ожидание 1 сек перед следующим запросом...")
                    time.sleep(1)
                    
            except Exception as e:
                logger.exception(f"Ошибка при обработке {hero['display_name']}")
                continue
        
        if all_data["heroes"]:
            save_to_json(all_data)
            logger.info(f"Успешно обработано {len(all_data['heroes'])}/{len(heroes)} героев")
        else:
            logger.warning("Не удалось собрать данные ни по одному герою")
        
        logger.info("=== ЗАВЕРШЕНИЕ РАБОТЫ СКРИПТА ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка в основном процессе")
        raise

if __name__ == "__main__":
    main(season="3.5")