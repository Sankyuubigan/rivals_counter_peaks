# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# --- ДИНАМИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПУТЕЙ ---
# Используем переменную окружения, установленную в build.py
project_root = os.environ.get('PROJECT_ROOT_FOR_SPEC')

# Fallback, если переменная не установлена (например, при запуске .spec напрямую)
if not project_root:
    print("WARNING (.spec): Переменная окружения PROJECT_ROOT_FOR_SPEC не найдена. Используется fallback-метод.")
    spec_dir = Path(SPECPATH).parent
    project_root = str(spec_dir.parent)

# Проверка, что корень проекта определен верно
if not os.path.isdir(project_root) or not os.path.exists(os.path.join(project_root, 'core', 'main.py')):
    raise FileNotFoundError(f"CRITICAL ERROR (.spec): Корень проекта определен неверно! Путь: {project_root}")

print(f"INFO (.spec): Корень проекта определен как: {project_root}")


# --- Определение пути к site-packages ---
import site
site_packages_paths = site.getsitepackages()
site_packages_path = ""
for p in site_packages_paths:
    if "site-packages" in p and os.path.isdir(p):
        site_packages_path = p
        break

if not site_packages_path:
    # Fallback для стандартной структуры venv
    site_packages_path = os.path.join(sys.prefix, 'Lib', 'site-packages')
    print(f"WARNING (.spec): Не удалось определить site-packages через site.getsitepackages(). Используется fallback: {site_packages_path}")
else:
    print(f"INFO (.spec): Директория site-packages найдена: {site_packages_path}")

if not os.path.isdir(site_packages_path):
    raise FileNotFoundError(f"CRITICAL ERROR (.spec): Директория site-packages не найдена: {site_packages_path}")


def find_dist_info_path(package_name, search_path):
    """Находит путь к .dist-info или .egg-info для пакета."""
    if not os.path.isdir(search_path): return None
    # Проверяем оба варианта имени: с дефисом и с подчеркиванием
    prefixes_to_check = {package_name.lower(), package_name.lower().replace('-', '_')}
    
    for item in os.listdir(search_path):
        item_lower = item.lower()
        if item_lower.endswith(('.dist-info', '.egg-info')) and os.path.isdir(os.path.join(search_path, item)):
            for prefix in prefixes_to_check:
                # Проверяем, что имя папки начинается с имени пакета и дефиса (например, "tqdm-4.6...")
                if item_lower.startswith(prefix + '-'):
                    return os.path.join(search_path, item)
    print(f"WARNING (.spec): .dist-info или .egg-info для '{package_name}' не найдена в '{search_path}'.")
    return None

# --- Сборка списка данных (datas) ---
datas_list = []

# ИЗМЕНЕНИЕ: Убран `tqdm`, так как хук для него удален и он больше не является критичной зависимостью.
dependencies_metadata = ['numpy']

for dep_name in dependencies_metadata:
    dist_info = find_dist_info_path(dep_name, site_packages_path)
    if dist_info:
        datas_list.append((dist_info, os.path.basename(dist_info)))
        print(f"INFO (.spec): Добавлены метаданные для {dep_name}: '{os.path.basename(dist_info)}'")
    else:
        print(f"WARNING (.spec): Метаданные для '{dep_name}' не найдены.")


# Добавление ресурсов приложения
datas_list.extend([
    (os.path.join(project_root, 'resources'), 'resources'),
    (os.path.join(project_root, 'database'), 'database'),
    (os.path.join(project_root, 'info'), 'info'),
    (os.path.join(project_root, 'vision_models'), 'vision_models')
])

# --- Сборка путей для поиска (pathex) ---
pathex_list = [
    project_root,
    os.path.join(project_root, 'core'),
    site_packages_path
]

a = Analysis(
    [os.path.join(project_root, 'core', 'main.py')],
    pathex=pathex_list,
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'pynput', 'mss', 'cv2', 'numpy', 'pyperclip', 'ctypes', 'markdown',
        'onnxruntime', 'tqdm', 'numba', 'psutil',
        'PySide6.QtNetwork', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'shiboken6',
    ],
    hookspath=[os.path.join(project_root, 'build_scripts')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='rivals_counter_peaks_25.09.05', # Имя будет заменено скриптом build.py
    icon=os.path.join(project_root, 'resources', 'logo.ico'),
    debug=False,
    console=False,
    windowed=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest=os.path.join(project_root, 'build_scripts', 'manifest.xml')
)