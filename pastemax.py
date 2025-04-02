import os
import sys
import pyperclip

def process_folder(folder_path):
    # Проверяем, существует ли папка
    if not os.path.isdir(folder_path):
        print(f"Ошибка: Папка '{folder_path}' не существует.")
        sys.exit(1)

    result = []

    # Рекурсивно обходим папку
    for root, dirs, files in os.walk(folder_path):
        # Игнорируем папку .git
        if '.git' in dirs:
            dirs.remove('.git')

        for file_name in files:
            file_path = os.path.join(root, file_name)
            # Получаем относительный путь от исходной папки
            relative_path = os.path.relpath(file_path, folder_path)

            try:
                # Читаем содержимое файла
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Если файл не текстовый (например, бинарный), пропускаем или записываем как "[binary file]"
                content = "[binary file]"
            except Exception as e:
                content = f"[error reading file: {str(e)}]"

            # Добавляем путь и содержимое в результат
            result.append(f"File: {relative_path}\n{content}\n---")

    # Объединяем все в один текст
    final_text = "\n".join(result)

    # Копируем в буфер обмена
    pyperclip.copy(final_text)
    print(f"Содержимое файлов из '{folder_path}' скопировано в буфер обмена!")

if __name__ == "__main__":
    # # Проверяем, передан ли аргумент с путём к папке
    # if len(sys.argv) != 2:
    #     print("Использование: python pastemax.py <путь_к_папке>")
    #     sys.exit(1)

    # folder_path = sys.argv[1]
    folder_path="./core"
    process_folder(folder_path)