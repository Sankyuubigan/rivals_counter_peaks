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

def get_heroes_list(season="1"):
    """Получает список всех героев со страницы characters с их глобальными статистиками"""
    logger.info(f"=== НАЧАЛО ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ (СЕЗОН {season}) ===")
    logger.info("Открываем страницу https://rivalsmeta.com/characters")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Устанавливаем таймауты и заголовки
        page.set_viewport_size({"width": 1200, "height": 800})
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        try:
            # Переходим на страницу с таймаутом
            logger.info("Загружаем страницу...")
            start_time = time.time()
            response = page.goto("https://rivalsmeta.com/characters", timeout=30000)
            
            # Проверяем статус ответа
            if response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                browser.close()
                return []
                
            load_time = time.time() - start_time
            logger.info(f"Страница загружена за {load_time:.2f} секунд")
            
            # Ждём загрузки контента
            logger.info("Ожидаем появления таблицы героев...")
            page.wait_for_selector("table", timeout=15000)
            
            # Проверяем текущие данные до выбора сезона
            logger.info("Проверяем данные до выбора сезона...")
            initial_data = page.evaluate('''() => {
                const table = document.querySelector('table');
                if (!table) return "No table";
                
                const firstRow = table.querySelector('tbody tr');
                if (!firstRow) return "No rows";
                
                const cells = firstRow.querySelectorAll('td');
                if (cells.length >= 4) {
                    return {
                        hero: cells[0].textContent.trim(),
                        winRate: cells[3].textContent.trim(),
                        pickRate: cells[4].textContent.trim(),
                        banRate: cells[5].textContent.trim(),
                        matches: cells[6].textContent.trim()
                    };
                }
                return "No data";
            }''')
            
            logger.info(f"Данные до выбора сезона: {initial_data}")
            
            # Пробуем выбрать сезон через select
            logger.info(f"Пробуем выбрать сезон {season} через select...")
            
            # Метод 1: Использование select element
            try:
                # Проверяем наличие select с id season_filter
                season_select = page.query_selector('#season_filter')
                if season_select:
                    logger.info("Найден select с id season_filter")
                    
                    # Получаем все опции
                    options = season_select.query_selector_all('option')
                    logger.info(f"Доступные опции сезона: {[option.text_content() for option in options]}")
                    
                    # Ищем опцию с нужным сезоном
                    season_value = None
                    for option in options:
                        option_text = option.text_content().strip()
                        if season in option_text:
                            season_value = option.get_attribute('value')
                            logger.info(f"Найдена опция '{option_text}' со значением '{season_value}'")
                            break
                    
                    if season_value:
                        # Выбираем сезон через значение
                        season_select.select_option(value=season_value)
                        logger.info(f"Сезон {season} выбран через select_option")
                        time.sleep(5)  # Ждем загрузки данных
                    else:
                        logger.warning(f"Не найдена опция для сезона {season}")
                else:
                    logger.warning("Не найден select с id season_filter")
            except Exception as e:
                logger.warning(f"Ошибка при выборе сезона через select: {str(e)}")
            
            # Метод 2: Пробуем через JavaScript
            if not season_value:
                try:
                    logger.info("Пробуем выбрать сезон через JavaScript...")
                    page.evaluate(f'''(season) => {{
                        const select = document.getElementById('season_filter');
                        if (select) {{
                            const options = select.querySelectorAll('option');
                            for (let option of options) {{
                                if (option.textContent.includes(season)) {{
                                    select.value = option.value;
                                    // Создаем событие change
                                    const event = new Event('change', {{ bubbles: true }});
                                    select.dispatchEvent(event);
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}''', season)
                    
                    logger.info(f"Сезон {season} выбран через JavaScript")
                    time.sleep(5)  # Ждем загрузки данных
                except Exception as e:
                    logger.warning(f"Ошибка при выборе сезона через JavaScript: {str(e)}")
            
            # Проверяем данные после выбора сезона
            logger.info("Проверяем данные после выбора сезона...")
            final_data = page.evaluate('''() => {
                const table = document.querySelector('table');
                if (!table) return "No table";
                
                const firstRow = table.querySelector('tbody tr');
                if (!firstRow) return "No rows";
                
                const cells = firstRow.querySelectorAll('td');
                if (cells.length >= 4) {
                    return {
                        hero: cells[0].textContent.trim(),
                        winRate: cells[3].textContent.trim(),
                        pickRate: cells[4].textContent.trim(),
                        banRate: cells[5].textContent.trim(),
                        matches: cells[6].textContent.trim()
                    };
                }
                return "No data";
            }''')
            
            logger.info(f"Данные после выбора сезона: {final_data}")
            
            # Ждем еще немного, чтобы убедиться, что данные загрузились
            logger.info("Ждем загрузки данных...")
            time.sleep(5)
            
            logger.info("Таблица найдена, начинаем обработку")
            
            # Извлекаем данные через JavaScript
            heroes_data = page.evaluate('''() => {
                const heroes = [];
                const table = document.querySelector('table');
                if (!table) return heroes;
                
                const rows = table.querySelectorAll('tbody tr');
                for (let i = 0; i < rows.length; i++) {
                    const row = rows[i];
                    const cells = row.querySelectorAll('td');
                    
                    if (cells.length >= 7) {  // Убедимся, что достаточно колонок
                        // Извлекаем имя героя из первой ячейки
                        let heroName = cells[0].textContent.trim();
                        
                        // Удаляем возможные лишние пробелы и символы
                        heroName = heroName.replace(/\\s+/g, ' ').trim();
                        
                        // Формируем URL-friendly версию
                        let urlName = heroName.toLowerCase()
                            .replace(/[^a-z0-9\\s-]/g, '')
                            .replace(/\\s+/g, '-')
                            .replace(/^-+|-+$/g, '');
                            
                        // Извлекаем глобальные статистики
                        const role = cells[1].textContent.trim();
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
                # Пропускаем пустые имена
                if not hero['display_name'] or hero['display_name'] == 'Hero':
                    continue
                
                # Пропускаем дубликаты
                if hero['url_name'] in seen_urls:
                    continue
                    
                seen_urls.add(hero['url_name'])
                valid_heroes.append(hero)
            
            logger.info(f"Отфильтровано до {len(valid_heroes)} валидных героев")
            
            # Логируем первые 5 героев для проверки
            logger.info("Первые 5 обнаруженных героев с их статистикой:")
            for i, hero in enumerate(valid_heroes[:5]):
                logger.info(f"  {i+1}. {hero['display_name']}: WR={hero['win_rate']}, PR={hero['pick_rate']}, BR={hero['ban_rate']}, M={hero['matches']}")
            
            # Сохраняем полный список в файл для отладки
            with open('heroes_debug.json', 'w', encoding='utf-8') as f:
                json.dump(valid_heroes, f, ensure_ascii=False, indent=2)
            
            browser.close()
            logger.info("=== ЗАВЕРШЕНИЕ ПОЛУЧЕНИЯ СПИСКА ГЕРОЕВ ===")
            return valid_heroes
            
        except Exception as e:
            logger.exception("Ошибка при получении списка героев")
            if 'browser' in locals():
                browser.close()
            return []

def get_matchups_data(hero_url_name, season="1"):
    """Получает данные матчапов для конкретного героя"""
    url = f"https://rivalsmeta.com/characters/{hero_url_name}/matchups"
    logger.info(f"=== НАЧАЛО ОБРАБОТКИ ГЕРОЯ: {hero_url_name.upper()} ===")
    logger.info(f"Загружаем данные матчапов по URL: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Устанавливаем таймауты и заголовки
        page.set_viewport_size({"width": 1200, "height": 800})
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        try:
            # Переходим на страницу
            logger.info("Загружаем страницу матчапов...")
            start_time = time.time()
            response = page.goto(url, timeout=30000)
            
            # Проверяем статус
            if response and response.status == 404:
                logger.warning(f"Страница матчапов не найдена для {hero_url_name} (404)")
                browser.close()
                return []
            elif response and response.status != 200:
                logger.error(f"Ошибка загрузки страницы: статус {response.status}")
                browser.close()
                return []
                
            load_time = time.time() - start_time
            logger.info(f"Страница загружена за {load_time:.2f} секунд")
            
            # Даем дополнительное время для полной загрузки JS-контента
            logger.info("Ждем дополнительные 5 секунд для полной загрузки динамического контента...")
            time.sleep(5)
            
            # Проверяем наличие таблиц с подходящими заголовками
            logger.info("Ищем таблицы матчапов...")
            
            try:
                page.wait_for_function("""
                    () => {
                        const tables = document.querySelectorAll('table');
                        for (const table of tables) {
                            const headers = table.querySelectorAll('th');
                            if (headers.length >= 4) {
                                const headerTexts = Array.from(headers).map(h => 
                                    h.textContent.trim().toLowerCase()
                                );
                                if (headerTexts.includes('hero') && 
                                    headerTexts.includes('win rate') && 
                                    headerTexts.includes('difference') && 
                                    headerTexts.includes('matches')) {
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                """, timeout=20000)
                
                logger.info("Найдены таблицы с нужными заголовками")
            except Exception as e:
                logger.warning(f"Не удалось найти таблицы по заголовкам: {str(e)}")
                browser.close()
                return []
            
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
                                .replace(/[^a-zA-Z\\s]/g, '')
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
            
            if matchups:
                logger.info("Примеры извлеченных данных:")
                for i, matchup in enumerate(matchups[:3]):
                    logger.info(f"  {i+1}. Противник: {matchup['opponent']}, "
                               f"Win Rate: {matchup['win_rate']}, "
                               f"Difference: {matchup['difference']}, "
                               f"Matches: {matchup['matches']}")
            else:
                logger.warning("Таблицы найдены, но данные не извлечены.")
            
            browser.close()
            logger.info("=== ЗАВЕРШЕНИЕ ОБРАБОТКИ ГЕРОЯ ===")
            return matchups
            
        except Exception as e:
            logger.exception(f"Ошибка при обработке героя {hero_url_name}")
            if 'browser' in locals():
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
        
        # Логируем статистику
        total_heroes = len(data)
        total_matchups = sum(len(hero_data.get('opponents', [])) for hero_data in data.values())
        logger.info(f"Статистика сохранения: {total_heroes} героев, {total_matchups} матчапов")
        
        return filename
    except Exception as e:
        logger.exception("Ошибка при сохранении данных в JSON")
        return None

def main(season="1"):
    """Основная функция"""
    logger.info(f"=== НАЧАЛО РАБОТЫ СКРИПТА (СЕЗОН {season}) ===")
    
    try:
        # Получаем список героев с их глобальной статистикой
        heroes = get_heroes_list(season)
        
        if not heroes:
            logger.error("Не удалось получить список героев. Завершение работы.")
            return
        
        logger.info(f"Обнаружено {len(heroes)} героев для обработки")
        
        # Создаем структуру для хранения всех данных в новом формате
        all_data = {}
        
        # Обрабатываем каждого героя
        for i, hero in enumerate(heroes):
            logger.info(f"--- Обработка героя {i+1}/{len(heroes)} ---")
            logger.info(f"Герой: {hero['display_name']} (URL: {hero['url_name']})")
            
            try:
                start_time = time.time()
                matchups = get_matchups_data(hero["url_name"], season)
                processing_time = time.time() - start_time
                
                # Формируем новую структуру данных
                hero_data = {
                    "win_rate": hero["win_rate"],
                    "pick_rate": hero["pick_rate"],
                    "ban_rate": hero["ban_rate"],
                    "matches": hero["matches"],
                    "role": hero["role"],
                    "tier": hero["tier"],
                    "opponents": matchups if matchups else []
                }
                
                all_data[hero["display_name"]] = hero_data
                
                logger.info(f"Успешно обработан {hero['display_name']} за {processing_time:.2f} сек")
                logger.info(f"  Глобальная статистика: WR={hero['win_rate']}, PR={hero['pick_rate']}, BR={hero['ban_rate']}, M={hero['matches']}")
                
                # Делаем паузу между запросами
                if i < len(heroes) - 1:
                    logger.info(f"Ожидание 2 сек перед следующим запросом...")
                    time.sleep(2)
                    
            except Exception as e:
                logger.exception(f"Ошибка при обработке {hero['display_name']}")
                continue
        
        # Сохраняем данные
        if all_data:
            save_to_json(all_data)
            logger.info(f"Успешно обработано {len(all_data)}/{len(heroes)} героев")
        else:
            logger.warning("Не удалось собрать данные ни по одному герою")
        
        logger.info("=== ЗАВЕРШЕНИЕ РАБОТЫ СКРИПТА ===")
        
    except Exception as e:
        logger.exception("Критическая ошибка в основном процессе")
        raise

if __name__ == "__main__":
    # Запуск скрипта для определенного сезона
    main(season="3")  # Можно изменить на нужный сезон