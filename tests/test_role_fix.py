"""
Тестовый скрипт для проверки исправления парсинга роли героя
Проверяет парсинг роли для ВСЕХ героев на странице
"""
import time
from playwright.sync_api import sync_playwright

def test_all_heroes_roles():
    playwright = sync_playwright().start()
    
    browser = playwright.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    page = context.new_page()
    page.set_default_timeout(30000)
    
    print("=== Открываем rivalsmeta.com/characters ===")
    page.goto("https://rivalsmeta.com/characters", wait_until='commit', timeout=30000)
    time.sleep(3)
    page.evaluate("window.scrollTo(0, 300)")
    time.sleep(2)
    
    # Ждём таблицу
    page.wait_for_selector('table', timeout=20000)
    
    # Тестируем исправленный парсинг роли для ВСЕХ героев
    print("\n=== Тест исправленного парсинга роли (ВСЕ герои) ===")
    heroes_data = page.evaluate("""() => {
        const heroes = [];
        const table = document.querySelector('table');
        if (!table) return heroes;
        
        const rows = table.querySelectorAll('tbody tr');
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.querySelectorAll('td');
            
            if (cells.length >= 7) {
                let heroName = cells[0].textContent.trim().replace(/\\s+/g, ' ').trim();
                
                let role = '';
                const roleImg = cells[1].querySelector('img.hero-class');
                if (roleImg) {
                    // Роль извлекаем из имени файла в src, т.к. alt содержит имя героя (баг сайта)
                    // Пример: /images/vanguard.png -> vanguard
                    const src = roleImg.getAttribute('src') || '';
                    const match = src.match(/\\/images\\/([a-z_-]+)\\.png/i);
                    if (match) {
                        role = match[1].charAt(0).toUpperCase() + match[1].slice(1);
                    }
                }
                if (!role) role = cells[1].textContent.trim();
                
                heroes.push({
                    name: heroName,
                    role: role,
                    roleSrc: cells[1].querySelector('img.hero-class')?.getAttribute('src') || 'N/A',
                    roleAlt: cells[1].querySelector('img.hero-class')?.getAttribute('alt') || 'N/A'
                });
            }
        }
        return heroes;
    }""")
    
    print(f"\nНайдено героев: {len(heroes_data)}")
    print("\n" + "="*80)
    print(f"{'#':<4} {'Имя героя':<25} {'Роль':<15} {'Статус':<10}")
    print("="*80)
    
    ok_count = 0
    fail_count = 0
    warn_count = 0
    
    for i, hero in enumerate(heroes_data, 1):
        # Проверка
        if hero['role'] == hero['name']:
            status = "FAIL"
            fail_count += 1
        elif hero['role'].lower() in ['vanguard', 'duelist', 'strategist']:
            status = "OK"
            ok_count += 1
        else:
            status = "WARN"
            warn_count += 1
        
        print(f"{i:<4} {hero['name']:<25} {hero['role']:<15} {status:<10}")
    
    print("="*80)
    print(f"\nИТОГО: OK={ok_count}, FAIL={fail_count}, WARN={warn_count}")
    
    if fail_count > 0:
        print("\n[FAIL] Есть герои с некорректной ролью!")
    else:
        print("\n[OK] Все роли спарсены корректно!")
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    
    context.close()
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    test_all_heroes_roles()
