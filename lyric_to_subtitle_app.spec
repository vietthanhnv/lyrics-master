# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Lyric-to-Subtitle App.

This file defines how to build a standalone executable for the application,
including all dependencies, data files, and platform-specific configurations.
"""

import sys
import os
from pathlib import Path

# Get the application directory
app_dir = Path(SPECPATH)
src_dir = app_dir / "src"

# Define the main script
main_script = str(src_dir / "main.py")

# Collect all Python files from src directory
def collect_src_files():
    """Collect all Python files from the src directory."""
    src_files = []
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            rel_path = py_file.relative_to(app_dir)
            src_files.append((str(py_file), str(rel_path.parent)))
    return src_files

# Hidden imports for AI models and PyQt6
hidden_imports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.QtMultimedia',
    
    # AI and ML libraries
    'torch',
    'torchaudio',
    'transformers',
    'librosa',
    'soundfile',
    'scipy',
    'numpy',
    
    # Audio processing
    'pydub',
    'demucs',
    'whisperx',
    
    # Subtitle formats
    'pysrt',
    'webvtt',
    
    # Translation services
    'deepl',
    'googletrans',
    
    # Utilities
    'requests',
    'tqdm',
    'yaml',
    'dotenv',
    
    # Application modules
    'src.main',
    'src.models',
    'src.services',
    'src.ui',
    'src.utils',
]

# Data files to include
datas = [
    # Include test audio file for initial setup
    ('data/hello.mp3', 'data'),
    
    # Include any configuration files
    ('pyproject.toml', '.'),
    ('README.md', '.'),
]

# Binaries to exclude (will be handled by conda/pip)
excludes = [
    'tkinter',
    'matplotlib.backends._backend_tk',
    'PIL.ImageTk',
    'PIL._imagingtk',
]

# Analysis configuration
a = Analysis(
    [main_script],
    pathex=[str(app_dir), str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Platform-specific executable configuration
if sys.platform == "win32":
    # Windows executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='LyricToSubtitleApp',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # Windows GUI application
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,  # Add icon path here if available
    )
    
elif sys.platform == "darwin":
    # macOS application bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='LyricToSubtitleApp',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='LyricToSubtitleApp'
    )
    
    app = BUNDLE(
        coll,
        name='LyricToSubtitleApp.app',
        icon=None,  # Add icon path here if available
        bundle_identifier='com.lyrictosubtitle.app',
        info_plist={
            'CFBundleName': 'Lyric-to-Subtitle App',
            'CFBundleDisplayName': 'Lyric-to-Subtitle App',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleIdentifier': 'com.lyrictosubtitle.app',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        }
    )
    
else:
    # Linux executable
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='LyricToSubtitleApp',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='LyricToSubtitleApp'
    )