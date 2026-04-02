"""
Тестовый скрипт для отладки парсинга роли героя с rivalsmeta.com
Открывает страницу и показывает фактическую HTML-структуру таблицы
"""
import time
from playwright.sync_api import sync_playwright

def test_role_parsing():
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
    
    # 1. Получаем HTML первых 3 строк таблицы
    print("\n=== HTML первых 3 строк таблицы ===")
    html_sample = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return 'TABLE NOT FOUND';
        const rows = table.querySelectorAll('tbody tr');
        let result = '';
        for (let i = 0; i < Math.min(3, rows.length); i++) {
            result += '--- ROW ' + i + ' ---\\n';
            result += rows[i].outerHTML + '\\n\\n';
        }
        return result;
    }""")
    print(html_sample)
    
    # 2. Получаем содержимое каждой ячейки первой строки
    print("\n=== Содержимое ячеек первого героя ===")
    cells_info = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return 'TABLE NOT FOUND';
        const row = table.querySelector('tbody tr');
        if (!row) return 'NO ROWS';
        
        const cells = row.querySelectorAll('td');
        let result = 'Всего ячеек: ' + cells.length + '\\n\\n';
        
        cells.forEach((cell, index) => {
            result += '--- CELL[' + index + '] ---\\n';
            result += 'Text: "' + cell.textContent.trim() + '"\\n';
            
            const img = cell.querySelector('img');
            if (img) {
                result += 'IMG alt: "' + img.alt + '"\\n';
                result += 'IMG title: "' + img.title + '"\\n';
                result += 'IMG src: "' + img.src + '"\\n';
            }
            
            // Показываем классы ячейки
            result += 'Classes: "' + cell.className + '"\\n';
            
            // Показываем все дочерние элементы
            const children = cell.children;
            result += 'Children count: ' + children.length + '\\n';
            for (let c = 0; c < children.length; c++) {
                result += '  Child[' + c + ']: tag=' + children[c].tagName + ', classes="' + children[c].className + '", text="' + children[c].textContent.trim() + '"\\n';
                const childImg = children[c].querySelector('img');
                if (childImg) {
                    result += '    IMG alt: "' + childImg.alt + '", title: "' + childImg.title + '"\\n';
                }
            }
            result += '\\n';
        });
        
        return result;
    }""")
    print(cells_info)
    
    # 3. Получаем заголовки таблицы
    print("\n=== Заголовки таблицы ===")
    headers = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return 'TABLE NOT FOUND';
        const ths = table.querySelectorAll('thead th, th');
        let result = '';
        ths.forEach((th, i) => {
            result += 'TH[' + i + ']: "' + th.textContent.trim() + '" classes="' + th.className + '"\\n';
            const img = th.querySelector('img');
            if (img) {
                result += '  IMG alt: "' + img.alt + '", title: "' + img.title + '"\\n';
            }
        });
        return result;
    }""")
    print(headers)
    
    # 4. Попробуем найти все img в таблице и их alt атрибуты
    print("\n=== Все img в первых 5 строках ===")
    imgs_info = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return 'TABLE NOT FOUND';
        const rows = table.querySelectorAll('tbody tr');
        let result = '';
        for (let i = 0; i < Math.min(5, rows.length); i++) {
            const imgs = rows[i].querySelectorAll('img');
            imgs.forEach((img, j) => {
                const cellIndex = Array.from(rows[i].querySelectorAll('td')).findIndex(td => td.contains(img));
                result += 'Row[' + i + '] Cell[' + cellIndex + '] img[' + j + ']: alt="' + img.alt + '", title="' + img.title + '", src="' + img.src + '"\\n';
            });
        }
        return result;
    }""")
    print(imgs_info)
    
    # 5. Попробуем найти tooltip или data-атрибуты с ролью
    print("\n=== Data-атрибуты и title в первых 3 строках ===")
    data_attrs = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return 'TABLE NOT FOUND';
        const rows = table.querySelectorAll('tbody tr');
        let result = '';
        for (let i = 0; i < Math.min(3, rows.length); i++) {
            const allEls = rows[i].querySelectorAll('*');
            allEls.forEach(el => {
                const attrs = el.attributes;
                let hasData = false;
                let attrStr = '';
                for (let a = 0; a < attrs.length; a++) {
                    if (attrs[a].name.startsWith('data-') || attrs[a].name === 'title') {
                        hasData = true;
                        attrStr += attrs[a].name + '="' + attrs[a].value + '" ';
                    }
                }
                if (hasData) {
                    result += 'Element: <' + el.tagName + ' class="' + el.className + '"> ' + attrStr + '\\n';
                }
            });
        }
        return result || 'No data-attributes found';
    }""")
    print(data_attrs)
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    
    context.close()
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    test_role_parsing()
