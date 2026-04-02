# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

project_root = os.environ.get('PROJECT_ROOT_FOR_SPEC')
if not project_root:
    spec_dir = Path(SPECPATH).parent
    project_root = str(spec_dir.parent)

import site
site_packages_paths = site.getsitepackages()
site_packages_path = ""
for p in site_packages_paths:
    if "site-packages" in p and os.path.isdir(p):
        site_packages_path = p
        break
if not site_packages_path:
    site_packages_path = os.path.join(sys.prefix, 'Lib', 'site-packages')

datas_list =[
    (os.path.join(project_root, 'resources'), 'resources'),
    (os.path.join(project_root, 'database'), 'database'),
    (os.path.join(project_root, 'info'), 'info')
]

pathex_list =[
    project_root,
    os.path.join(project_root, 'core'),
    site_packages_path
]

a = Analysis([os.path.join(project_root, 'core', 'main.py')],
    pathex=pathex_list,
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'pynput', 'pyperclip', 'ctypes', 'markdown', 'psutil', 'websockets',
        'PySide6.QtNetwork', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'shiboken6',
    ],
    hookspath=[os.path.join(project_root, 'build_scripts')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'tensorflow', 'tensorboard',
        'scipy', 'pandas', 'matplotlib', 'numba', 'llvmlite', 'cv2', 'onnxruntime', 'mss', 'PIL',
        'IPython', 'jupyter_client', 'jupyter_core', 'nbformat', 'nbconvert', 'ipykernel',
        'jedi', 'parso', 'PyQt5', 'tkinter', 'black', 'blib2to3', 'pytest', 'transformers',
    ],
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
    a.datas,[],
    name='rivals_counter_peaks_26.04.02',
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