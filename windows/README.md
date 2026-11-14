# BuscadorYT para Windows

Compilación del ejecutable `BuscadorYT.exe` (onefile, "windowed", sin consola).

## Qué hay aquí

| Fichero | Para qué sirve |
|---|---|
| `BuscadorYT.spec` | Receta de PyInstaller para Windows (un único `.exe`, sin BUNDLE ni args de macOS). |
| `BuscadorYT.ico` | Icono del ejecutable, generado desde `../android/icon.png`. |

La compilación se hace en **GitHub Actions** (runner `windows-latest`), porque
PyInstaller no hace cross-compilación: no se puede generar un `.exe` de Windows
desde macOS/Linux directamente. El workflow está en
`.github/workflows/build.yml` y se dispara con un tag `v*` (o manualmente desde
la pestaña "Actions").

## Compilar en local (si tienes una máquina Windows)

```powershell
python -m pip install -r ..\requirements.txt pyinstaller
pyinstaller --clean --noconfirm BuscadorYT.spec
# → dist\BuscadorYT.exe
```

## Notas

- El código de la app es el mismo (`../BuscadorYT.py`); Windows usa `%APPDATA%\BuscadorYT\`
  como carpeta de datos (ver `../paths.py`).
- En Windows el diálogo de "Exportar a PDF" y el de "Abrir base de datos" son
  los nativos de Qt (funcionan sin los apaños de Android).
