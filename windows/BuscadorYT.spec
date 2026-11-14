# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para BuscadorYT en WINDOWS.
#
# Genera un único BuscadorYT.exe (onefile, "windowed", sin consola).
# A diferencia de BuscadorYT.spec (macOS), aquí NO hay BUNDLE ni argumentos
# específicos de macOS (argv_emulation/codesign/entitlements).
#
# Uso (en Windows):  pyinstaller --clean --noconfirm BuscadorYT_win.spec

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# reportlab necesita sus fuentes/codificaciones empaquetadas para generar PDF.
# youtube_transcript_api se incluye por si algún import se hace de forma dinámica.
for pkg in ("reportlab", "youtube_transcript_api", "requests", "fastembed"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# RAG: rag.py se importa de forma dinámica desde la UI; onnxruntime aporta
# las librerías nativas que ejecutan el modelo de embeddings local.
hiddenimports += ["rag", "onnxruntime", "numpy", "tokenizers", "huggingface_hub"]

# Módulos Qt que la app no usa: se excluyen para no hinchar el ejecutable.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D", "PySide6.QtQuickControls2", "PySide6.QtQmlModels",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
    "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml",
    "PySide6.QtDesigner", "PySide6.QtUiTools", "PySide6.QtHelp",
    "PySide6.QtStateMachine", "PySide6.QtScxml",
]

a = Analysis(
    ["BuscadorYT.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BuscadorYT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # sin terminal (GUI)
    disable_windowed_traceback=False,
    icon="windows/BuscadorYT.ico",      # icono de Windows
)
