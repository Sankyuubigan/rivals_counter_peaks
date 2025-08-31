# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# ВАЖНО: Путь к корню проекта. Убедитесь, что он правильный!
project_root = r'D:\Projects\rivals_counter_peaks'

if not os.path.isdir(project_root):
    print(f"CRITICAL ERROR (.spec): Жестко прописанный project_root НЕ СУЩЕСТВУЕТ или не является директорией: {project_root}")
print(f"INFO (.spec): Корень проекта (жестко задан) определен как: {project_root}")

# --- Определение пути к site-packages ---
import site
python_exe_path = sys.executable
print(f"INFO (.spec): Python executable: {python_exe_path}")

# Определяем site-packages из текущего Python интерпретатора
venv_root_determined = Path(sys.prefix)
site_packages_list = site.getsitepackages()

if site_packages_list and python_exe_path.lower().endswith(('python.exe', 'python3.exe')):
    # Используем site-packages из выполняемого интерпретатора
    site_packages_path_candidate = Path(site_packages_list[0])
    if site_packages_path_candidate.exists() and site_packages_path_candidate.name == "site-packages":
        site_packages_path = site_packages_path_candidate
        print(f"INFO (.spec): Используется site-packages из текущего интерпретатора: {site_packages_path}")
    else:
        print(f"WARNING (.spec): Неподходящий путь site-packages: {site_packages_path_candidate}")
        site_packages_path = venv_root_determined / 'Lib' / 'site-packages'
else:
    # Fallback to default venv structure
    site_packages_path = venv_root_determined / 'Lib' / 'site-packages'
    print(f"WARNING (.spec): Используется fallback путь к site-packages: {site_packages_path}")

if not os.path.isdir(site_packages_path):
    print(f"CRITICAL WARNING (.spec): Директория site-packages не найдена: {site_packages_path}")
else:
    print(f"INFO (.spec): Подтверждена директория site-packages: {site_packages_path}")

transformers_models_dir_in_site_packages = os.path.join(site_packages_path, 'transformers', 'models')
if not os.path.isdir(transformers_models_dir_in_site_packages):
    print(f"WARNING (.spec): Директория transformers/models не найдена в site-packages: {transformers_models_dir_in_site_packages}")
    transformers_models_dir_in_site_packages = None

def find_dist_info_path(package_name, search_path):
    if not os.path.isdir(search_path): print(f"WARNING (.spec): search_path '{search_path}' не директория."); return None
    normalized_package_name_for_search = package_name.replace('-', '_')
    for item in os.listdir(search_path):
        item_lower = item.lower()
        if item_lower.endswith('.dist-info') and os.path.isdir(os.path.join(search_path, item)):
            dist_info_pkg_part = item_lower.split('-')[0]
            if dist_info_pkg_part == normalized_package_name_for_search or dist_info_pkg_part == package_name.lower(): return os.path.join(search_path, item)
        if item_lower.endswith('.egg-info') and os.path.isdir(os.path.join(search_path, item)):
            egg_info_pkg_part_simple = item_lower.replace('.egg-info', ''); egg_info_pkg_part_complex = egg_info_pkg_part_simple.split('-')[0]
            if egg_info_pkg_part_simple == normalized_package_name_for_search or egg_info_pkg_part_complex == normalized_package_name_for_search or \
               egg_info_pkg_part_simple == package_name.lower() or egg_info_pkg_part_complex == package_name.lower():
                print(f"WARNING (.spec): Найдена .egg-info для {package_name}: {item}."); return os.path.join(search_path, item)
    print(f"WARNING (.spec): .dist-info или .egg-info для '{package_name}' не найдена в '{search_path}'."); return None

datas_list = []
dependencies_to_process_metadata = ['tqdm', 'transformers', 'regex', 'requests', 'packaging', 'filelock', 'safetensors', 'pyyaml', 'huggingface-hub', 'tokenizers']
for dep_name in dependencies_to_process_metadata:
    dist_info = find_dist_info_path(dep_name, site_packages_path)
    if dist_info: datas_list.append((dist_info, os.path.basename(dist_info))); print(f"INFO (.spec): Добавление {dep_name} dist-info: '{dist_info}' -> '{os.path.basename(dist_info)}'")
    else:
        if dep_name in ['tqdm', 'transformers', 'pyyaml', 'regex', 'requests', 'packaging', 'filelock', 'safetensors']: print(f"CRITICAL WARNING (.spec): .dist-info для '{dep_name}' НЕ НАЙДЕН!")
        else: print(f"WARNING (.spec): .dist-info для '{dep_name}' не найден.")

try:
    transformers_package_dir_init = os.path.join(site_packages_path, 'transformers')
    models_init_py_source = os.path.join(transformers_package_dir_init, 'models', '__init__.py')
    models_init_py_dest_dir = os.path.join('transformers', 'models').replace(os.sep, '/')
    if os.path.isfile(models_init_py_source):
        datas_list.append((models_init_py_source, models_init_py_dest_dir))
        print(f"INFO (.spec): Явно добавлен transformers.models.__init__.py: {models_init_py_source} -> в директорию {models_init_py_dest_dir}")
    else:
        print("CRITICAL WARNING (.spec): Не удалось найти исходный файл transformers/models/__init__.py: {models_init_py_source}")
except Exception as e_spec_tf_models_init:
    print(f"WARNING (.spec): Ошибка при попытке явного добавления transformers/models/__init__.py: {e_spec_tf_models_init}")

datas_list.extend([
    (os.path.join(project_root, 'resources'), 'resources'),
    (os.path.join(project_root, 'database', 'heroes_bd.py'), 'database'),
    (os.path.join(project_root, 'database', 'roles_and_groups.py'), 'database'),
    (os.path.join(project_root, 'database', 'marvel_rivals_stats_20250831-030213.json'), 'database'),
    (os.path.join(project_root, 'database', 'heroes_compositions.json'), 'database'),
    (os.path.join(project_root, 'database', 'roles.json'), 'database'),
    (os.path.join(project_root, 'core', 'lang', 'information_ru.md'), os.path.join('core', 'lang')),
    (os.path.join(project_root, 'core', 'lang', 'information_en.md'), os.path.join('core', 'lang')),
    (os.path.join(project_root, 'core', 'lang', 'author_ru.md'), os.path.join('core', 'lang')),
    (os.path.join(project_root, 'core', 'lang', 'author_en.md'), os.path.join('core', 'lang')),
    (os.path.join(project_root, 'vision_models'), 'vision_models')
])

pathex_list = [
    project_root,
    os.path.join(project_root, 'core'),
    str(site_packages_path)
]
if transformers_models_dir_in_site_packages:
    pathex_list.append(transformers_models_dir_in_site_packages)
    print(f"INFO (.spec): Добавлен путь в pathex: {transformers_models_dir_in_site_packages}")

a = Analysis(
    [os.path.join(project_root, 'core', 'main.py')],
    pathex=pathex_list,
    binaries=[], datas=datas_list,
    hiddenimports=[
        'pynput', 'mss', 'cv2', 'numpy', 'pyperclip', 'ctypes', 'markdown',
        'onnxruntime', 'tqdm', 'transformers', 'tokenizers', 'huggingface_hub',
        'safetensors', 'filelock', 'requests', 'packaging', 'regex', 'yaml',
        'PySide6.QtNetwork', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'shiboken6',
        'transformers.models',
        'transformers.models.__init__',
        'transformers.models.auto',
        'transformers.modeling_utils',
        'transformers.configuration_utils',
        'transformers.models.dinov2',
        'transformers.models.dinov2.modeling_dinov2',
        'transformers.models.dinov2.configuration_dinov2',
    ],
    hookspath=[os.path.join(project_root, 'core', 'build_scripts')],
    hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=None, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='rivals_counter_peaks_25.08.31',
    icon=r'd:\Projects\rivals_counter_peaks\resources\logo.ico',
    debug=False,         # <--- ИЗМЕНЕНО НА False
    console=False,       # <--- ИЗМЕНЕНО НА False
    windowed=True,       # <--- ИЗМЕНЕНО НА True (или просто удалить, это по умолчанию для графических)
    bootloader_ignore_signals=False,
    strip=False, upx=True, # Можно попробовать включить UPX для уменьшения размера (если нет проблем)
    upx_exclude=[], runtime_tmpdir=None,
    disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None,
    manifest=os.path.join(project_root, 'build_scripts', 'manifest.xml')
)