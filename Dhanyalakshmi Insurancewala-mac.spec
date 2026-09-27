# -*- mode: python ; coding: utf-8 -*-
#
# macOS build spec. PyInstaller cannot cross-compile: this file must be run
# with `pyinstaller "Dhanyalakshmi Insurancewala-mac.spec"` on an actual Mac
# (or a `macos-latest` GitHub Actions runner - see .github/workflows/build-mac.yml),
# never from Windows.
#
# The resulting .app is unsigned/unnotarized, so macOS Gatekeeper will show an
# "unidentified developer" warning on first launch (right-click > Open to bypass).
# Full notarization requires a paid Apple Developer ID and is not set up here.

a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static')],
    hiddenimports=['main', 'models', 'database', 'import_csv', 'app_paths',
                   'passlib.handlers.pbkdf2', 'passlib.handlers.sha2_crypt'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Dhanyalakshmi Insurancewala',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Dhanyalakshmi Insurancewala',
)

app = BUNDLE(
    coll,
    name='Dhanyalakshmi Insurancewala.app',
    icon=None,  # TODO: supply an .icns once a logo asset exists (build via `iconutil` on macOS)
    bundle_identifier='com.dhanyalakshmiinsurancewala.erp',
    info_plist={
        'CFBundleName': 'Dhanyalakshmi Insurancewala',
        'CFBundleDisplayName': 'Dhanyalakshmi Insurancewala',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'NSHumanReadableCopyright': 'Dhanyalakshmi Insurancewala',
    },
)
