# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('icons', 'icons')],
    hiddenimports=[
        # Our own modules: the app dir contains __init__.py, which makes
        # PyInstaller treat it as a package and miss plain sibling imports.
        'enforcer',
        'sleep_enforcer',
        'coach',
        'coach.schemas',
        'coach.store',
        'coach.classifier',
        'coach.recommender',
        'coach.explainer',
        'coach.patterns',
        'coach.activity',
        'pages',
        'pages.coach_page',
        'pages.data_page',
        'pages.feedback_page',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
version = "1.4.0"
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    #exclude_binaries=True,
    name=f'sleep_enforcer-v{version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\app_icon.ico'],
)
