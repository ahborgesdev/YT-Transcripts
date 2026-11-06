# YT Transcripts

Aplicación de escritorio (PySide6/Qt) para descargar transcripciones de YouTube,
leerlas con comodidad y **preguntarles** con búsqueda semántica local y respuestas
citadas. Todo el texto y el índice viven en archivos SQLite en tu equipo: puedes
tener una base por tema (`costura.db`, `cocina.db`…) con su propio índice.

![Preguntar a las transcripciones](_captura_preguntar_guia.png)

## Qué hace

- **Descargar** la transcripción de un vídeo de YouTube a partir de su URL o ID
  (español, inglés o automático), con una pausa de seguridad entre descargas.
- **Guardar** la biblioteca en una base SQLite con nombre (`transcripts.db` por
  defecto, o la que elijas al arrancar), ordenada por fecha.
- **Leer** con tamaño de letra ajustable, enlace al vídeo en el navegador y
  exportación a PDF.
- **Preguntar**: índice semántico local (embeddings ONNX) + redactor opcional
  que responde citando los pasajes, con las citas clicables.
- **Cuaderno**: guarda las preguntas y respuestas en un PDF que se va ampliando
  (`cuaderno-<nombre>.pdf`), con fecha, la respuesta y **los pasajes exactos** en
  los que se apoya (el mismo texto que abre la cita en la app, no solo el enlace
  al vídeo).
- **Elegir la IA**: sin IA (solo pasajes), DeepSeek en la nube u Ollama en local.

## Requisitos

- macOS (Apple Silicon) para la app empaquetada de este repositorio.
- Python 3.12+ si trabajas desde el código.
- Opcional: [Ollama](https://ollama.com) para redactar respuestas en local.
- Opcional: clave de API de [DeepSeek](https://platform.deepseek.com) para la nube.

## Uso rápido

1. La primera vez ponle nombre a la base de datos (o deja `transcripts`).
2. Pega la URL del vídeo y pulsa **Descargar transcripción**.
3. Selecciona la transcripción en la lista para leerla.
4. En la pestaña **Preguntar**, pulsa **Indexar** una vez (la primera vez descarga
   un modelo de ~240 MB) y después escribe tu pregunta. Con **Añadir al cuaderno**
   guardas la respuesta en el PDF de esa base.
5. En **Ajustes** eliges el redactor, la clave API, el tamaño de letra y los datos
   del índice. El **selector de base de datos** de la cabecera (y el menú del mismo
   nombre) te permite cambiar de tema o crear una base nueva sin cerrar la app.

La guía completa para usuarios está en
[docs/Guia-de-uso-YT-Transcripts.pdf](docs/Guia-de-uso-YT-Transcripts.pdf)
(fuente editable: [DOCX](Guia-de-uso-YT-Transcripts.docx)).

## Cómo funciona el RAG

```
transcripts → chunks (~900 caracteres) → embeddings locales ONNX (384 dims)
                                                      ↓
pregunta → embedding → coseno top-6 → pasajes → redactor (IA) → respuesta [1] [2]
                                                      ↘ sin redactor: solo pasajes
```

- **Índice**: tablas `chunks`, `chunk_vec` y `rag_meta` dentro de la base activa
  (cada base por tema tiene su propio índice). Se actualiza de forma incremental
  (hash del contenido + nombre del modelo).
- **Embeddings**: `paraphrase-multilingual-MiniLM-L12-v2` (fastembed/ONNX, 384
  dimensiones, 50 idiomas), ejecutado en CPU, sin conexión.
- **Redactor**: cualquier API compatible con OpenAI. Por defecto DeepSeek
  (`deepseek-chat`); también Ollama (`http://localhost:11434/v1`) u otro servicio.
- **Citas**: cada `[n]` es un enlace que abre la transcripción y resalta el pasaje.

### IA local con Ollama

```bash
ollama pull qwen2.5:7b-instruct   # ~4,7 GB
ollama serve
```

Después, en **Ajustes** → Redactor: «Ollama · local» → **Detectar** → elegir el
modelo → **Probar conexión** → **Guardar**.

## Datos y privacidad

| Archivo | Contenido |
|---|---|
| `<nombre>.db` | transcripciones, índice semántico, preguntas guardadas y control de cambios |
| `cuaderno-<nombre>.pdf` | cuaderno de preguntas y respuestas de esa base |
| `rag_config.json` | redactor, dirección, modelo y clave API (si hay) |
| `ui_config.json` | preferencias de interfaz (tamaño de letra y base activa) |
| `models/` | modelo de embeddings descargado en la primera indexación |

Sin redactor, o con Ollama, **nada sale del equipo**: solo se descargan subtítulos
de YouTube cuando lo pides. Con un redactor en la nube se envían la pregunta y los
seis pasajes recuperados, nunca la base de datos completa.

## Desarrollo

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python BuscadorYT.py        # abrir la aplicación
.venv/bin/python rag.py index         # indexar por consola
.venv/bin/python rag.py search "consulta" -k 6
.venv/bin/python rag.py stats
```

### Compilar

macOS, en local:

```bash
PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache" \
  .venv/bin/pyinstaller --clean --noconfirm BuscadorYT.spec
# → dist/BuscadorYT
```

Windows 10+: PyInstaller no cross-compila, así que se compila en GitHub Actions
(`windows-latest`, ver `.github/workflows/build.yml`) o en una máquina Windows.
El ejecutable queda en `dist/BuscadorYT.exe`.

## Responsividad (mobile-first)

La interfaz se adapta al ancho lógico (dp) con *breakpoints*, al estilo de
Bootstrap pero sin CSS (`responsive.py`):

| Ancho | Modo | Qué cambia |
|---|---|---|
| < 600 dp | `compact` | cabecera apilada, splitter en vertical, formularios con la etiqueta **encima** del campo, botones con *wrap* |
| 600–900 dp | `medium` | escritorio estrecho: cabecera apilada y sidebar más delgado |
| > 900 dp | `wide` | disposición de escritorio (lista a la izquierda, texto a la derecha) |

Las filas de formulario (`FieldRow`) miran además **su propio ancho**: por
debajo de 460 dp la etiqueta pasa encima del campo, aunque la ventana vaya en
`medium`. Los botones usan `FlowLayout`, que hace wrap en vez de comprimirse.

### Modo lectura

El lector puede ocupar toda la ventana, sin lista ni registro: botón **⛶** en la
fila del lector, **F11**, o **doble clic** en una transcripción de la lista.
Se sale con **Esc** o el mismo botón. Dentro del modo lectura aparece además
el botón **▭** para alternar entre *columna cómoda* (≈720 dp, centrada) y *todo
el ancho*. El zoom de letra sigue disponible (A− / A+, Ctrl + rueda y pellizco
del trackpad).

### Vista previa (devtools de escritorio)

Igual que estirar la ventana en las herramientas del navegador:

```bash
python3 preview_responsive.py                 # Ajustes en móvil, tableta y escritorio
python3 preview_responsive.py --tab all       # las tres pestañas
python3 preview_responsive.py --sizes 432x960,800x1280 --open
python3 preview_responsive.py --live 432x960  # ventana real a ese tamaño
```

Deja las capturas en `preview/` y genera `preview/index.html` para compararlas
de un vistazo (con el breakpoint activo marcado en cada una).

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `BuscadorYT.py` | interfaz, SQLite, descarga de subtítulos, exportación a PDF |
| `rag.py` | troceado, embeddings, índice, búsqueda y llamada al redactor |
| `responsive.py` | breakpoints, `FieldRow` y `FlowLayout` (mobile-first) |
| `preview_responsive.py` | capturas a tamaños de móvil, tableta y PC + galería HTML |
| `BuscadorYT.spec` | receta de empaquetado con PyInstaller |
| `make_guia.py` | genera la guía de uso (DOCX → PDF) |
| `RAG.md` | documentación técnica del índice y de los proveedores de IA |
| `docs/` | guía de uso en PDF |

## Licencias

| Componente | Licencia |
|---|---|
| PySide6 / Qt | LGPL-3.0 |
| reportlab | BSD |
| youtube-transcript-api | MIT |
| fastembed | Apache-2.0 |
| onnxruntime | MIT |
| numpy | BSD |
| Modelo MiniLM (paraphrase-multilingual) | Apache-2.0 |
