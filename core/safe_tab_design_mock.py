#!/usr/bin/env python3
"""
Безопасный дизайн tab mode - НОВАЯ МАКЕТНАЯ ВЕРСИЯ

Основные принципы:
1. НЕТ конвертирования layout (горизонтальный -> вертикальный и наоборот)
2. statическая структура с заранее созданными контейнерами
3. управление только видимостью контейнеров
4. безопасное управление Qt widget lifecycle
"""

import sys

# Mock Qt классы для тестирования без зависимостей
class MockQt:
    AlignRight = 2
    AlignLeft = 1
    AlignVCenter = 4
    AlignHCenter = 4
    ScrollBarAlwaysOff = 1

class MockQObject:
    def __init__(self):
        self._parent = None

class MockQWidget(MockQObject):
    def __init__(self, parent=None):
        super().__init__()
        self._parent = parent
        self.visible = True
        self._layout = None
        self._max_height = None
        self._stylesheet = ""
        self._object_name = ""
        self._children = []

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def setVisible(self, visible):
        self.visible = visible

    def setLayout(self, layout):
        if self._layout:
            self._layout._parent = None
        self._layout = layout
        if layout:
            layout._parent = self

    def setMaximumHeight(self, height):
        self._max_height = height

    def setStyleSheet(self, stylesheet):
        self._stylesheet = stylesheet

    def setObjectName(self, name):
        self._object_name = name

    def findChild(self, child_type, name):
        return None

class MockQLayout(MockQObject):
    def __init__(self):
        super().__init__()
        self.items = []
        self._contents_margins = (0, 0, 0, 0)
        self._spacing = 0
        self._alignment = 0

    def count(self):
        return len(self.items)

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def addWidget(self, widget, stretch=0):
        if widget and widget != self._parent:
            self.items.append(("widget", widget, stretch))
            widget.setParent(self._parent)
        return len(self.items)

    def setContentsMargins(self, left, top, right, bottom):
        self._contents_margins = (left, top, right, bottom)

    def setSpacing(self, spacing):
        self._spacing = spacing

    def setAlignment(self, alignment):
        self._alignment = alignment

    def addStretch(self, stretch=1):
        self.items.append(("stretch", None, stretch))

class MockQVBoxLayout(MockQLayout):
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            parent.setLayout(self)

class MockQHBoxLayout(MockQLayout):
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            parent.setLayout(self)

class MockQScrollArea(MockQWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget_resizable = True

    def setWidgetResizable(self, resizable):
        self.widget_resizable = resizable

class MockQFrame(MockQWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

# Импорт mock классов
Qt = MockQt()
QVBoxLayout = MockQVBoxLayout
QHBoxLayout = MockQHBoxLayout
QWidget = MockQWidget
QScrollArea = MockQScrollArea
QFrame = MockQFrame

class SafeTabModeManager:
    """
    Безопасный менеджер tab mode с новой структурой

    НОВАЯ АРХИТЕКТУРА:
    - Основной контейнер: QVBoxLayout в scroll area
    - Два отдельных горизонтальных списка: enemies и counters
    - Никаких конвертирований layout!
    """

    def __init__(self):
        # Основной scroll area (существующий из основного UI)
        self.icons_scroll_area = QScrollArea()
        self.icons_scroll_area.setWidgetResizable(True)

        # Основной вертикальный layout для tab mode
        self.tab_mode_main_layout = QVBoxLayout()
        self.tab_mode_main_layout.setSpacing(5)
        self.tab_mode_main_layout.setContentsMargins(5, 2, 5, 2)

        # Создаем два контейнера для двух рядов
        self._create_enemies_container()
        self._create_counters_container()

        # Добавляем оба контейнера в основной layout
        self.tab_mode_main_layout.addWidget(self.enemies_container)
        self.tab_mode_main_layout.addWidget(self.counters_container)

        # Создаем scroll content и устанавливаем layout
        self.scroll_content = QWidget()
        self.scroll_content.setLayout(self.tab_mode_main_layout)
        self.icons_scroll_area.setWidget(self.scroll_content)

        print("✓ SafeTabModeManager инициализирован")

    def _create_enemies_container(self):
        """Создает верхний контейнер для врагов (красная рамка, выравнивание вправо)"""
        self.enemies_container = QWidget()
        self.enemies_container.setObjectName("enemies_container")

        # Красная рамка вокруг врагов
        self.enemies_container.setStyleSheet("""
            QWidget#enemies_container {
                border: 2px solid red;
                border-radius: 4px;
                padding: 2px;
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # Layout для врагов
        self.enemies_layout = QHBoxLayout(self.enemies_container)
        self.enemies_layout.setContentsMargins(2, 2, 2, 2)
        self.enemies_layout.setSpacing(4)
        # Враги выравниваются ВПРАВО
        self.enemies_layout.setAlignment(Qt.AlignRight)

        # Ограничение высоты для одного ряда
        self.enemies_container.setMaximumHeight(65)

        print("✓ Enemies container создан (красная рамка, выравнивание вправо)")

    def _create_counters_container(self):
        """Создает нижний контейнер для рейтинг героев (без рамки, выравнивание влево)"""
        self.counters_container = QWidget()
        self.counters_container.setObjectName("counters_container")

        # БЕЗ рамки для нижней панели
        self.counters_container.setStyleSheet("""
            QWidget#counters_container {
                border: none;
                padding: 0px;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

        # Layout для героев рейтинга
        self.counters_layout = QHBoxLayout(self.counters_container)
        self.counters_layout.setContentsMargins(2, 2, 2, 2)
        self.counters_layout.setSpacing(4)
        # Герои выравниваются ВЛЕВО
        self.counters_layout.setAlignment(Qt.AlignLeft)

        # Ограничение высоты для одного ряда
        self.counters_container.setMaximumHeight(65)

        print("✓ Counters container создан (без рамки, выравнивание влево)")

    def enter_tab_mode(self):
        """Вход в таб режим - просто показываем все контейнеры"""
        print("=== ВХОД В TAB MODE ===")

        # Показываем основной scroll area
        self.icons_scroll_area.show()

        # Показываем оба контейнера
        self.enemies_container.show()
        self.counters_container.show()

        print("✓ Icons scroll area показан")
        print("✓ Enemies container показан (верхний ряд)")
        print("✓ Counters container показан (нижний ряд)")
        print("✓ Tab mode активен")

    def exit_tab_mode(self):
        """Выход из таб режима - прячем все контейнеры"""
        print("=== ВЫХОД ИЗ TAB MODE ===")

        # Прячем основной scroll area
        self.icons_scroll_area.hide()

        print("✓ Icons scroll area скрыт")
        print("✓ Tab mode деактивирован")

    def is_safe_design(self):
        """Проверяет безопасность дизайна"""
        checks = []

        # 1. Нет конвертирования layout (основной принцип безопасности)
        current_layout_type = type(self.tab_mode_main_layout).__name__
        checks.append(("Нет конвертирования layout", current_layout_type == "QVBoxLayout"))

        # 2. Статическая структура
        has_enemies_container = hasattr(self, 'enemies_container') and self.enemies_container
        has_counters_container = hasattr(self, 'counters_container') and self.counters_container
        checks.append(("Статическая структура", has_enemies_container and has_counters_container))

        # 3. Правильные выравнивания
        enemies_right_aligned = "AlignRight" in str(self.enemies_layout._alignment) if hasattr(self.enemies_layout, '_alignment') else False
        counters_left_aligned = "AlignLeft" in str(self.counters_layout._alignment) if hasattr(self.counters_layout, '_alignment') else False
        checks.append(("Правильное выравнивание", enemies_right_aligned and counters_left_aligned))

        return checks

def test_safe_tab_mode():
    """Тестирует новый безопасный дизайн tab mode"""
    print("=== ТЕСТИРОВАНИЕ НОВОГО БЕЗОПАСНОГО TAB MODE ===")

    # Создаем менеджер
    manager = SafeTabModeManager()

    # Проверяем безопасность дизайна
    print("\n=== ПРОВЕРКА БЕЗОПАСНОСТИ ДИЗАЙНА ===")
    safety_checks = manager.is_safe_design()
    for check_name, passed in safety_checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}: {passed}")

    all_safe = all(passed for _, passed in safety_checks)
    if all_safe:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОШЛИ - ДИЗАЙН БЕЗОПАСЕН!")
    else:
        print("\n❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОШЛИ - ДИЗАЙН НУЖДАЕТ В ИСПРАВЛЕНИЯХ!")

    # Тестируем вход/выход из tab mode
    print("\n=== ТЕСТИРОВАНИЕ ВХОДА/ВЫХОДА ===")

    # Вход в tab mode
    manager.enter_tab_mode()

    # Проверяем состояние
    enemies_visible = manager.enemies_container.visible
    counters_visible = manager.counters_container.visible
    scroll_visible = manager.icons_scroll_area.visible

    print(f"\nПосле входа в tab mode:")
    print(f"✓ Enemies container видимый: {enemies_visible}")
    print(f"✓ Counters container видимый: {counters_visible}")
    print(f"✓ Icons scroll area видимый: {scroll_visible}")

    # Выход из tab mode
    manager.exit_tab_mode()

    # Проверяем состояние
    scroll_hidden = not manager.icons_scroll_area.visible
    print(f"\nПосле выхода из tab mode:")
    print(f"✓ Icons scroll area скрыт: {scroll_hidden}")

    print("\n=== ТЕСТ ЗАВЕРШЕН ===")

    success = all_safe and enemies_visible and counters_visible and scroll_visible and scroll_hidden

    if success:
        print("🎉 ТЕСТ ПРОШЕЛ УСПЕШНО - НОВЫЙ ДИЗАЙН ГОТОВ К ИНТЕГРАЦИИ!")
    else:
        print("❌ ТЕСТ НЕ ПРОШЕЛ - ТРЕБУЮТСЯ ДОРАБОТКИ!")

    return success

if __name__ == "__main__":
    success = test_safe_tab_mode()
    sys.exit(0 if success else 1)