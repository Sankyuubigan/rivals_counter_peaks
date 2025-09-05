import tkinter as tk
from tkinter import ttk
from global_hotkeys import *
import threading
import time

class TabAwareApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TAB Режим - Поверх всех окон + Счетчик")
        self.root.geometry("450x350")
        
        # Переменная для отслеживания состояния TAB
        self.tab_pressed = False
        
        # Счетчик для нажатий TAB+0
        self.counter = 0
        
        # Создаем элементы интерфейса
        self.setup_ui()
        
        # Настраиваем хоткеи
        self.setup_hotkeys()
        
        # Запускаем проверку хоткеев в отдельном потоке
        self.hotkey_thread = threading.Thread(target=self.start_hotkey_listener, daemon=True)
        self.hotkey_thread.start()
        
        # Привязываем закрытие окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Основной фрейм
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Метка для отображения состояния
        self.status_label = ttk.Label(
            self.main_frame, 
            text="Обычный режим\n(Нажмите и удерживайте TAB)", 
            font=("Arial", 14),
            foreground="blue"
        )
        self.status_label.pack(pady=10)
        
        # Фрейм для счетчика (изначально скрыт)
        self.counter_frame = ttk.Frame(self.main_frame)
        self.counter_label = ttk.Label(
            self.counter_frame,
            text="Счетчик TAB+0: 0",
            font=("Arial", 16, "bold"),
            foreground="red"
        )
        self.counter_label.pack(pady=5)
        
        # Инструкция для счетчика
        self.counter_instruction = ttk.Label(
            self.counter_frame,
            text="Нажмите 0 (при зажатом TAB) для увеличения счетчика",
            font=("Arial", 10),
            foreground="orange"
        )
        self.counter_instruction.pack(pady=2)
        
        # Текстовое поле для демонстрации
        self.text_area = tk.Text(
            self.main_frame, 
            height=8, 
            width=45,
            font=("Arial", 10),
            bg="lightgray",
            fg="black"
        )
        self.text_area.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Вставляем начальный текст
        self.text_area.insert(tk.END, "Это обычный режим работы.\n\n")
        self.text_area.insert(tk.END, "Когда вы нажмете и удерживаете TAB:\n")
        self.text_area.insert(tk.END, "• Окно станет поверх всех окон\n")
        self.text_area.insert(tk.END, "• Интерфейс изменится\n")
        self.text_area.insert(tk.END, "• Появится счетчик\n")
        self.text_area.insert(tk.END, "• Нажимайте 0 для увеличения счетчика\n")
        self.text_area.insert(tk.END, "• Будет видно поверх игр!\n\n")
        self.text_area.insert(tk.END, "Отпустите TAB для возврата в обычный режим.")
        self.text_area.config(state=tk.DISABLED)
        
        # Кнопка для демонстрации
        self.demo_button = ttk.Button(
            self.main_frame, 
            text="Демонстрационная кнопка",
            command=self.on_button_click
        )
        self.demo_button.pack(pady=10)
        
        # Информационная метка
        self.info_label = ttk.Label(
            self.main_frame,
            text="Окно в обычном режиме",
            font=("Arial", 9),
            foreground="gray"
        )
        self.info_label.pack(pady=5)
    
    def setup_hotkeys(self):
        """Настройка глобальных хоткеев"""
        # Определяем биндинги для TAB и 0 (отдельно)
        self.bindings = [
            {
                "hotkey": "tab",
                "on_press_callback": self.on_tab_press,
                "on_release_callback": self.on_tab_release,
                "actuate_on_partial_release": False,
            },
            {
                "hotkey": "0",
                "on_press_callback": self.on_zero_press,
                "on_release_callback": None,
                "actuate_on_partial_release": False,
            }
        ]
        
        # Регистрируем хоткеи
        register_hotkeys(self.bindings)
    
    def start_hotkey_listener(self):
        """Запуск слушателя хоткеев"""
        print("Запуск слушателя хоткеев...")
        start_checking_hotkeys()
    
    def on_tab_press(self):
        """Обработчик нажатия TAB"""
        if not self.tab_pressed:
            self.tab_pressed = True
            print("TAB нажат - переключение в режим TAB (поверх всех окон)")
            
            # Обновляем UI в главном потоке
            self.root.after(0, self.enable_tab_mode)
    
    def on_tab_release(self):
        """Обработчик отпускания TAB"""
        if self.tab_pressed:
            self.tab_pressed = False
            print("TAB отпущен - возврат в обычный режим")
            
            # Обновляем UI в главном потоке
            self.root.after(0, self.disable_tab_mode)
    
    def on_zero_press(self):
        """Обработчик нажатия 0"""
        if self.tab_pressed:
            # TAB нажат - увеличиваем счетчик
            self.counter += 1
            print(f"0 нажат при зажатом TAB! Счетчик: {self.counter}")
            
            # Обновляем счетчик в главном потоке
            self.root.after(0, self.update_counter_display)
            
            # Добавляем запись в текстовое поле
            self.root.after(0, lambda: self.add_counter_message())
        else:
            # TAB не нажат - игнорируем
            pass  # Ничего не делаем, можно добавить отладку если нужно
    
    def update_counter_display(self):
        """Обновление отображения счетчика"""
        self.counter_label.config(text=f"Счетчик: {self.counter}")
        
        # Добавляем визуальный эффект при изменении счетчика
        self.counter_label.config(foreground="lime")
        self.root.after(100, lambda: self.counter_label.config(foreground="red"))
    
    def add_counter_message(self):
        """Добавление сообщения о счетчике в текстовое поле"""
        if self.tab_pressed:
            self.text_area.config(state=tk.NORMAL)
            self.text_area.insert(tk.END, f"\n🔢 Нажатие 0! Счетчик: {self.counter}")
            self.text_area.see(tk.END)  # Прокрутка к концу
            self.text_area.config(state=tk.DISABLED)
    
    def enable_tab_mode(self):
        """Включение режима TAB - окно поверх всех окон"""
        # Показываем фрейм со счетчиком
        self.counter_frame.pack(pady=10, before=self.text_area)
        
        # Делаем окно поверх всех окон
        self.root.attributes('-topmost', True)
        
        # Дополнительные атрибуты для лучшей видимости в играх
        self.root.attributes('-alpha', 0.95)  # Небольшая прозрачность
        
        # Меняем цвет фона окна
        self.root.configure(bg="darkblue")
        self.main_frame.configure(style="Tab.TFrame")
        
        # Меняем стиль метки
        self.status_label.configure(
            text="🔥 РЕЖИМ TAB АКТИВЕН! 🔥\n(Окно поверх всех окон)",
            foreground="white",
            background="darkblue"
        )
        
        # Обновляем счетчик
        self.counter_label.config(
            text=f"Счетчик: {self.counter}",
            foreground="red",
            background="darkblue"
        )
        self.counter_instruction.config(
            foreground="orange",
            background="darkblue"
        )
        
        # Меняем стиль текстового поля
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, "🚀 РЕЖИМ TAB АКТИВЕН! 🚀\n\n")
        self.text_area.insert(tk.END, "✅ Окно теперь поверх всех окон!\n")
        self.text_area.insert(tk.END, "✅ Видно даже в играх!\n")
        self.text_area.insert(tk.END, "✅ Интерфейс изменен\n")
        self.text_area.insert(tk.END, "✅ Счетчик активен\n\n")
        self.text_area.insert(tk.END, "🎮 Удерживайте TAB и нажимайте 0!\n")
        self.text_area.insert(tk.END, "🎮 Каждое нажатие 0 увеличивает счетчик\n")
        self.text_area.insert(tk.END, "🎮 Можно нажимать много раз подряд!\n\n")
        self.text_area.insert(tk.END, "Отпустите TAB для возврата в обычный режим.")
        self.text_area.config(
            bg="black",
            fg="lime",
            font=("Courier", 9, "bold")
        )
        self.text_area.config(state=tk.DISABLED)
        
        # Меняем стиль кнопки
        self.demo_button.configure(
            text="🔥 КНОПКА В РЕЖИМЕ TAB 🔥",
            style="Tab.TButton"
        )
        
        # Меняем информационную метку
        self.info_label.configure(
            text="⚡ ОКНО ПОВЕРХ ВСЕХ ОКОН ⚡",
            foreground="red",
            font=("Arial", 10, "bold")
        )
        
        # Создаем специальные стили для режима TAB
        style = ttk.Style()
        style.configure("Tab.TFrame", background="darkblue")
        style.configure("Tab.TButton", foreground="red", font=("Arial", 12, "bold"))
        
        # Поднимаем окно на передний план
        self.root.lift()
        self.root.attributes('-topmost', True)  # Повторяем на всякий случай
        
        print("Окно установлено поверх всех окон. Счетчик активен. Нажимайте 0!")
    
    def disable_tab_mode(self):
        """Отключение режима TAB - возврат в обычный режим"""
        # Скрываем фрейм со счетчиком
        self.counter_frame.pack_forget()
        
        # Убираем свойство "поверх всех окон"
        self.root.attributes('-topmost', False)
        
        # Возвращаем нормальную прозрачность
        self.root.attributes('-alpha', 1.0)
        
        # Возвращаем обычный цвет фона
        self.root.configure(bg="SystemButtonFace")
        self.main_frame.configure(style="TFrame")
        
        # Возвращаем обычный стиль метки
        self.status_label.configure(
            text="Обычный режим\n(Нажмите и удерживайте TAB)",
            foreground="blue",
            background="SystemButtonFace"
        )
        
        # Возвращаем обычный стиль текстового поля
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, "Это обычный режим работы.\n\n")
        self.text_area.insert(tk.END, "Когда вы нажмете и удерживаете TAB:\n")
        self.text_area.insert(tk.END, "• Окно станет поверх всех окон\n")
        self.text_area.insert(tk.END, "• Интерфейс изменится\n")
        self.text_area.insert(tk.END, "• Появится счетчик\n")
        self.text_area.insert(tk.END, "• Нажимайте 0 для увеличения счетчика\n")
        self.text_area.insert(tk.END, "• Будет видно поверх игр!\n\n")
        self.text_area.insert(tk.END, "Отпустите TAB для возврата в обычный режим.")
        self.text_area.config(
            bg="lightgray",
            fg="black",
            font=("Arial", 10)
        )
        self.text_area.config(state=tk.DISABLED)
        
        # Возвращаем обычный стиль кнопки
        self.demo_button.configure(
            text="Демонстрационная кнопка",
            style="TButton"
        )
        
        # Возвращаем обычный стиль информационной метки
        self.info_label.configure(
            text="Окно в обычном режиме",
            foreground="gray",
            font=("Arial", 9)
        )
        
        print("Окно возвращено в обычный режим. Счетчик скрыт.")
    
    def on_button_click(self):
        """Обработчик нажатия кнопки"""
        if self.tab_pressed:
            message = f"🔥 Кнопка нажата в режиме TAB! Счетчик: {self.counter}"
            color = "lime"
        else:
            message = "Кнопка нажата в обычном режиме!"
            color = "blue"
        
        # Показываем сообщение
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"\n{message}")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        
        print(message)
    
    def on_closing(self):
        """Обработчик закрытия окна"""
        print("Закрытие приложения...")
        stop_checking_hotkeys()
        self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        print("Приложение запущено. Управление:")
        print("• Удерживайте TAB - режим поверх всех окон")
        print("• В режиме TAB нажимайте 0 - увеличение счетчика")
        print("• Можно нажимать 0 много раз подряд!")
        print("• Отпустите TAB - возврат в обычный режим")
        print("Для выхода закройте окно.")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("Приложение завершено.")
        finally:
            # Останавливаем проверку хоткеев
            try:
                stop_checking_hotkeys()
            except:
                pass
            print("Слушатель хоткеев остановлен.")

if __name__ == "__main__":
    app = TabAwareApp()
    app.run()