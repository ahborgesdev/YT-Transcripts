# YT Transcripts para Android

Empaquetado de `../BuscadorYT.py` como APK con **pyside6-android-deploy**
(PySide6 6.12 + python-for-android + buildozer). El código de escritorio no se
modifica: esta carpeta es una capa de arranque y empaquetado.

> Estado: **APK compilada, instalada y usada** en una TCL 9469X (Android 16,
> 1440×2200), con el icono definitivo. Verificado en el dispositivo: arranque,
> layout, base de datos, lista, visor, `cacert.pem` y descarga real de una
> transcripción desde la propia app.

## Compilar

```bash
./build.sh                 # normal (descarga NDK/SDK la primera vez)
./build-skip-sdk-update.sh # si sdkmanager no puede actualizar platform-tools
```

`build-skip-sdk-update.sh` hace el apaño para entornos sin salida a
dl.google.com o con el `sdkmanager` antiguo roto: deja los ficheros de
despliegue, pone `android.skip_update = True` en `buildozer.spec` y compila
con buildozer. También redirige `GRADLE_USER_HOME` y `ANDROID_USER_HOME`
dentro del proyecto (Gradle ignora `$HOME` y escribe en `user.home`).

> Noviembre de 2026: APK recompilada con la UI nueva (responsive, modo
> lectura, registro con interruptor) y los módulos `paths.py`/`responsive.py`.

## Contenido

| Fichero | Para qué sirve |
|---|---|
| `main.py` | **Entrada obligatoria** para el despliegue: crea `QApplication`, mueve los datos al directorio privado de la app, instala las CAs y abre la ventana en modo móvil. |
| `mobile.py` | Reorganiza la ventana para móvil/tablet: una columna, sin menú/registro, pestañas visibles y PDF oculto. |
| `rag_android.py` | RAG ligero para Android: BM25 local sobre `transcripts.db` + redacción opcional por API (misma API que `rag.py`). |
| `app/` | Copia de `../BuscadorYT.py` que refresca `build.sh` (no se edita aquí). |
| `vendor/` | Dependencias puras de Python empaquetadas dentro de la APK (requests, youtube-transcript-api…). Se genera con `scripts/prepare_vendor.py`. |
| `icon.png` | Icono definitivo (1024×1024, RGBA): tarjeta violeta ampliada, sin marco negro y con esquinas transparentes. |
| `pysidedeploy.spec` | Configuración de `pyside6-android-deploy` (título, wheels, arquitectura, buildozer). |
| `build.sh` | Prepara el entorno, descarga NDK/SDK y lanza el despliegue. |
| `install.sh` | Instala la última APK con `adb`. |
| `scripts/` | Utilidades: preparar `vendor/`, descargar SDK/NDK y previsualizar el layout. |
| `requirements-build.txt` | Herramientas del host (buildozer, Cython, pkginfo…); **no** van en la APK. |

## Requisitos

* **macOS o Linux** (el despliegue Android de PySide6 no funciona en Windows).
* **Python 3.10–3.14** en el host (probado con 3.14.6).
* **JDK 17** (`java -version` debe funcionar; `JAVA_HOME` apunta a él).
* **PySide6 6.12**: `build.sh` reutiliza el del sistema o lo instala en
  `../.venv-android`.
* **~8 GB libres**: la primera vez descarga NDK r28c + SDK (~1,5 GB) y
  compila CPython para el móvil. Además buildozer, Gradle y p4a usan
  `~/.buildozer` y `~/.gradle` (2–3 GB más); el NDK/SDK va a
  `~/.pyside6_android_deploy`.
* Móvil o emulador **Android 9+ (API 28), arm64-v8a**.
* Opcional: `autoconf`, `automake`, `libtool` y `pkg-config`
  (`brew install autoconf automake libtool pkg-config`) por si
  python-for-android compila alguna dependencia.

## Uso

```bash
cd android
./build.sh                # 1ª vez: descarga SDK/NDK y compila (20–40 min)
./build.sh --skip-sdk     # siguientes compilaciones (mucho más rápidas)
./build.sh --clean        # borra deployment/, dist/ y buildozer.spec
```

Salida: `android/dist/*.apk` (debug, arm64). Para instalarla:

```bash
adb devices
./install.sh              # o: adb install -r dist/<archivo>.apk
```

En el móvil aparece como **BuscadorYT**. El primer arranque crea una base
`transcripts.db` vacía en el almacenamiento privado de la app (no se copia la
base del escritorio).

### Qué está comprobado (sin APK)

* `scripts/preview_mobile.py` renderiza la ventana a 360×800 (captura en
  `../.android-build/preview_mobile.png`) sin errores: título, lista, visor y botones caben.
* `vendor/` importa con `python -S` (sin site-packages) y una descarga real
  (`fetch_transcript` + `fetch_video_meta`) funciona usando esas copias.
* RAG probado con una base real: 611 fragmentos indexados, búsqueda BM25 con
  acentos y pestaña «Preguntar» completa en modo recuperación (sin clave).
* En la tablet: índice automático (1 vídeo → 32 fragmentos) y pregunta
  «Termux» con 3 pasajes y 2 fuentes; sin clave se muestran los pasajes.
* El flujo completo de la ventana (`_start_download` → hilo → señal →
  SQLite → lista → visor) funciona en modo móvil offscreen.
* Generada e instalada la APK `dist/BuscadorYT-0.1-arm64-v8a-debug.apk`.
* En la tablet: arranca, muestra la lista desde `files/transcripts.db`, el
  visor y el icono nuevo; el bundle de CAs se escribe en `files/cacert.pem`.
* Descarga real desde la app en la tablet validada (p. ej. «Termux: todo lo
  que necesitas saber», subtítulos en español): red, CAs, SQLite e hilos OK.

## Cómo funciona

1. `build.sh` copia `../BuscadorYT.py` a `app/` y crea `vendor/` con
   `pip install --target` (sin extensiones nativas: todas las dependencias
   son Python puro).
2. `pyside6-android-deploy` extrae las recetas de PySide6/Shiboken6 de los
   wheels oficiales, genera `buildozer.spec` y deja que buildozer/python-for-
   android construyan CPython y empaqueten la APK.
3. `main.py` arranca dentro de Android:
   * añade `app/` y `vendor/` a `sys.path`;
   * redirige `APP_DIR`, `transcripts.db`, `ui_config.json` y
     `rag_config.json` a `QStandardPaths.AppDataLocation`
     (`/data/user/0/org.BuscadorYT.BuscadorYT/files`);
   * escribe `cacert.pem` (generado desde certifi) y apunta
     `REQUESTS_CA_BUNDLE` a él, porque Android no tiene `/etc/ssl/certs`;
   * aplica `mobile.apply_mobile_layout()` antes de mostrar la ventana.

### Por qué se empaqueta `vendor/`

`pyside6-android-deploy` fija `requirements = python3,shiboken6,PySide6` y no
instala paquetes de PyPI en el destino. Por eso `requests`,
`youtube-transcript-api` y sus dependencias viajan como código dentro de la
APK y se importan desde `vendor/`.

## Limitaciones actuales

* **RAG por BM25, no semántico**: `fastembed`/`numpy` (ONNX) no se pueden
  empaquetar, así que la búsqueda es por palabras clave (con acentos
  normalizados). La redacción con IA funciona con cualquier API compatible
  con OpenAI introduciendo la clave en «Ajustes» (DeepSeek, OpenRouter… o un
  Ollama/LM Studio del Mac accesible por LAN).
* **Sin cuaderno PDF**: `reportlab` no está incluido; se ocultan el botón de
  exportar y los botones del cuaderno. Las preguntas no se guardan en PDF.
* **Interfaz móvil básica**: es la ventana de escritorio en una columna; está
  pensada para funcionar, no para ser bonita. Los títulos largos se recortan
  con puntos suspensivos en la lista.
* **Sólo arm64-v8a** (`arch = aarch64`). Para x86_64 hay que descargar los
  wheels x86_64 y cambiar el spec.
* **APK debug** sin firma de release; el icono definitivo ya va incluido.
* **Datos aislados**: la base de datos del escritorio no se importa
  automáticamente; la app arranca con una base vacía.
* `pyside6-android-deploy` es *technical preview*: un fallo de python-for-
  android puede requerir limpiar cachés.

## Notas de compilación en macOS

`build.sh` ya incorpora los parches necesarios para compilar en macOS y en
entornos sin PTY ni Homebrew escribible:

* cmake se instala con pip en el venv y un shim de `brew` responde a las
  consultas de p4a (que en macOS exige el cmake de Homebrew).
* Si el `make` del sistema es GNU 3.81, se compila GNU make 4.4.1 en
  `.android-build/tools/`. Un wrapper le da un `TMPDIR` escribible porque p4a
  no lo propaga al entorno mínimo de las recetas.
* Si `pty.openpty()` no funciona, se activa un parche para que `sh` use
  tuberías en vez de pseudo-terminales.
* Se genera `cacert.pem` en la caché para que pip/buildozer descarguen con
  HTTPS aunque el Python del host no tenga CAs instaladas.

## Problemas frecuentes

**`JAVA_HOME` o «Java Runtime not found»**
```bash
brew install --cask temurin@17   # o el JDK 17 que ya uses
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

**Licencias del SDK / sdkmanager se queda parado**
`scripts/setup_android_sdk.py` acepta licencias con `accept_license=True`.
Si el SDK está corrupto, borra `~/.pyside6_android_deploy` y repite.

**La APK compila pero no arranca**
```bash
adb logcat -s python:* AndroidRuntime:E Qt:* | head -100
```
`main.py` guarda además el rastro en `<datos>/crash.log`. El error típico es
un `ModuleNotFoundError`: añade el paquete a `scripts/prepare_vendor.py` y
vuelve a compilar.

**Falla al compilar CPython/python-for-android**
Es la parte más frágil (depende de Xcode, autotools y del Python del host).
Prueba otro intérprete 3.10–3.14 con `PYTHON=/ruta/a/python3.x ./build.sh`
y, si el error viene de una caché a medias, `./build.sh --clean` y borra
`~/.buildozer/android/platform/build-*`.

**Cambios que no aparecen**
`build.sh` copia `../BuscadorYT.py` en cada ejecución; si editas `app/` a mano
se sobrescribe. Para limpiar del todo: `./build.sh --clean` y, si hace falta,
`rm -rf ~/.buildozer/android/platform/build-*`.

**Probar el layout sin compilar**
```bash
../.venv/bin/python scripts/preview_mobile.py 360 800
# -> ../.android-build/preview_mobile.png
```

## Próximos pasos sugeridos

1. Firmar una release si algún día hace falta publicar; la APK debug ya cubre
   el uso personal en la tablet.
2. Sustituir la lista/visor por una navegación por pantallas (lista →
   transcripción) para aprovechar el alto de la pantalla.
3. Probar la redacción real desde la tablet introduciendo la clave API en
   «Ajustes» (DeepSeek u otro proveedor compatible).

Los wheels y el SDK se descargan en `../.android-build/` y
`~/.pyside6_android_deploy`; no se versionan.
