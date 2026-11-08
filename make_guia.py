"""Genera la guía de uso de YT Transcripts (DOCX) para exportarla a PDF."""

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ACCENT = RGBColor(0x5B, 0x4B, 0xD6)
DARK = RGBColor(0x24, 0x24, 0x2E)
MUTED = RGBColor(0x63, 0x63, 0x74)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT_HEX = "5B4BD6"
SOFT_HEX = "F1EFFE"
TOPIC_HEX = "F7F7FB"

doc = Document()

# ── Propiedades ──────────────────────────────
core = doc.core_properties
core.title = "YT Transcripts — Guía de uso"
core.subject = "Descarga, lectura y consulta de transcripciones de YouTube"
core.author = "YT Transcripts"
core.comments = "Guía para quien recibe la aplicación"

# ── Página y estilos ─────────────────────────
section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.2)
section.bottom_margin = Cm(2.0)
section.left_margin = Cm(2.2)
section.right_margin = Cm(2.2)

normal = doc.styles["Normal"]
normal.font.name = "Arial"
normal.font.size = Pt(10.5)
normal.font.color.rgb = DARK
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.18

h1 = doc.styles["Heading 1"]
h1.font.name = "Arial"
h1.font.size = Pt(16)
h1.font.bold = True
h1.font.color.rgb = ACCENT
h1.paragraph_format.space_before = Pt(16)
h1.paragraph_format.space_after = Pt(4)
h1.paragraph_format.keep_with_next = True

h2 = doc.styles["Heading 2"]
h2.font.name = "Arial"
h2.font.size = Pt(12)
h2.font.bold = True
h2.font.color.rgb = DARK
h2.paragraph_format.space_before = Pt(10)
h2.paragraph_format.space_after = Pt(3)
h2.paragraph_format.keep_with_next = True


# ── Utilidades ───────────────────────────────
def shade(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def table_borders(table, color="DEDCEA"):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def cell_text(cell, text, bold=False, size=9.5, color=DARK):
    cell.text = ""
    par = cell.paragraphs[0]
    par.paragraph_format.space_after = Pt(2)
    par.paragraph_format.space_before = Pt(2)
    run = par.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.name = "Arial"


def tabla(cabeceras, filas, anchos=None):
    table = doc.add_table(rows=1, cols=len(cabeceras))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table_borders(table)
    for i, cab in enumerate(cabeceras):
        cell = table.rows[0].cells[i]
        shade(cell, ACCENT_HEX)
        cell_text(cell, cab, bold=True, color=WHITE)
        if anchos:
            cell.width = Cm(anchos[i])
    # la cabecera se repite si la tabla salta de página
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    cab_rep = OxmlElement("w:tblHeader")
    cab_rep.set(qn("w:val"), "true")
    tr_pr.append(cab_rep)

    for n, fila in enumerate(filas):
        cells = table.add_row().cells
        for i, valor in enumerate(fila):
            cell_text(cells[i], valor)
            if n % 2 == 1:
                shade(cells[i], TOPIC_HEX)
            if anchos:
                cells[i].width = Cm(anchos[i])
    for row in table.rows:   # ninguna fila se corta entre páginas
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def vineta(texto, negrita_hasta=None):
    par = doc.add_paragraph(style="List Bullet")
    par.paragraph_format.space_after = Pt(2)
    par.paragraph_format.left_indent = Cm(0.6)
    if negrita_hasta:
        r1 = par.add_run(negrita_hasta)
        r1.bold = True
        r1.font.size = Pt(10.5)
        par.add_run(texto).font.size = Pt(10.5)
    else:
        par.add_run(texto).font.size = Pt(10.5)
    return par


def aviso(texto):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.2)
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(8)
    p_pr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), SOFT_HEX)
    p_pr.append(shd)
    run = par.add_run(texto)
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x38, 0x2F, 0x8F)
    return par


def imagen(ruta, ancho_cm, leyenda):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(2)
    par.add_run().add_picture(ruta, width=Cm(ancho_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    run = cap.add_run(leyenda)
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED


def pie_de_pagina():
    footer = section.footer
    par = footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run("YT Transcripts · Guía de uso · página ")
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "636374")
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "17")
    r_pr.append(color)
    r_pr.append(size)
    r.append(r_pr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    par._p.append(fld)


pie_de_pagina()

# ── Portada ──────────────────────────────────
espacio = doc.add_paragraph()
espacio.paragraph_format.space_after = Pt(60)

titulo = doc.add_paragraph()
titulo.paragraph_format.space_after = Pt(0)
run = titulo.add_run("YT Transcripts")
run.bold = True
run.font.size = Pt(34)
run.font.color.rgb = ACCENT

sub = doc.add_paragraph()
sub.paragraph_format.space_after = Pt(2)
run = sub.add_run("Guía de uso")
run.font.size = Pt(20)
run.font.color.rgb = DARK

desc = doc.add_paragraph()
desc.paragraph_format.space_after = Pt(18)
run = desc.add_run("Descarga, lee y pregunta a tus transcripciones de YouTube")
run.font.size = Pt(12)
run.font.color.rgb = MUTED

linea = doc.add_paragraph()
linea.paragraph_format.space_after = Pt(14)
p_pr = linea._p.get_or_add_pPr()
p_bdr = OxmlElement("w:pBdr")
bottom = OxmlElement("w:bottom")
bottom.set(qn("w:val"), "single")
bottom.set(qn("w:sz"), "18")
bottom.set(qn("w:space"), "1")
bottom.set(qn("w:color"), ACCENT_HEX)
p_bdr.append(bottom)
p_pr.append(p_bdr)

meta = doc.add_paragraph()
meta.paragraph_format.space_after = Pt(2)
run = meta.add_run("Versión 1.1 · Noviembre de 2026")
run.font.size = Pt(10)
run.font.color.rgb = MUTED

meta2 = doc.add_paragraph()
run = meta2.add_run("Documento de acompañamiento de la aplicación (macOS · Apple Silicon)")
run.font.size = Pt(10)
run.font.color.rgb = MUTED

doc.add_page_break()

# ── 1. Qué es ────────────────────────────────
doc.add_heading("1. Qué es YT Transcripts", level=1)
doc.add_paragraph(
    "Es una aplicación de escritorio para macOS que convierte vídeos de YouTube en texto "
    "consultable. Descargas la transcripción de un vídeo, queda guardada en tu equipo y, "
    "a partir de ahí, puedes leerla con comodidad, exportarla a PDF o hacer preguntas "
    "sobre ella y recibir respuestas que citan el pasaje exacto del que salen."
)
doc.add_paragraph(
    "Todo vive en tu disco: una base de datos SQLite con los textos y el índice semántico. "
    "No hay servidor propio ni servicio de búsqueda externo."
)

doc.add_heading("Qué no hace", level=2)
vineta("No descarga el vídeo ni el audio: solo la pista de subtítulos cuando existe.")
vineta("No edita ni publica nada en YouTube; el vídeo se abre en tu navegador si lo pides.")
vineta("No inventa respuestas: si la información no está en tus transcripciones, lo dice.")

tabla(
    ["Capacidad", "Dónde se nota"],
    [
        ["Descargar transcripciones", "Panel izquierdo, con soporte de español e inglés"],
        ["Biblioteca local", "Base de datos SQLite junto a la aplicación"],
        ["Búsqueda por significado", "Índice semántico local (embeddings ONNX)"],
        ["Respuestas redactadas", "Pestaña Preguntar, con redactor local o en la nube"],
        ["Exportar a PDF", "Botón «Exportar a PDF» de la biblioteca"],
    ],
    anchos=[5.6, 11.0],
)

# ── 2. Arranque rápido ───────────────────────
doc.add_heading("2. Arranque rápido", level=1)
doc.add_paragraph("Tres pasos y ya estás preguntando:")
vineta("Pega la dirección del vídeo (o su ID de 11 caracteres) y pulsa «Descargar transcripción».",
       "1. Descarga. ")
vineta("Selecciona la transcripción en «Tus transcripciones»; el texto aparece a la derecha.",
       "2. Lee. ")
vineta("Ve a la pestaña «Preguntar», pulsa «Indexar» una vez y después escribe tu pregunta.",
       "3. Pregunta. ")

aviso("La primera indexación descarga un modelo de búsqueda de unos 240 MB y puede tardar "
      "unos minutos. Es solo la primera vez: después el índice se actualiza de forma "
      "incremental, solo con los vídeos nuevos o modificados.")

# ── 3. Descargar ─────────────────────────────
doc.add_heading("3. Descargar una transcripción", level=1)
doc.add_paragraph(
    "En el campo de la izquierda puedes pegar la URL completa o solo el ID. Se aceptan "
    "direcciones del tipo watch?v=…, youtu.be/…, /shorts/…, /live/… y /embed/…, además del "
    "identificador de 11 caracteres."
)
vineta("Elige el idioma de la transcripción: español, inglés o automático (lo que ofrezca el vídeo).",
       "Idioma. ")
vineta("Entre descarga y descarga la app espera 10 segundos a propósito, para que YouTube no "
       "bloquee tu conexión por exceso de peticiones.", "Pausa de seguridad. ")
vineta("Si algo falla, el panel «Registro» de abajo explica qué ha pasado y qué hacer.",
       "Registro. ")

doc.add_heading("Si el vídeo no tiene subtítulos", level=2)
doc.add_paragraph(
    "La app trabaja con los subtítulos que publica YouTube. Si el vídeo no los tiene, no hay "
    "nada que descargar; el registro mostrará el error correspondiente."
)

# ── 4. Biblioteca ────────────────────────────
doc.add_heading("4. Tu biblioteca", level=1)
doc.add_paragraph(
    "La lista «Tus transcripciones» muestra los vídeos guardados, del más reciente al más "
    "antiguo, con su canal y el idioma de la transcripción. Debajo hay tres acciones:"
)
tabla(
    ["Botón", "Qué hace"],
    [
        ["Modificar", "Cambia el título con el que se guarda y se muestra la transcripción."],
        ["Exportar a PDF", "Genera un PDF del texto, con el título, la URL del vídeo y el pie «Página N de M»."],
        ["Eliminar", "Borra la transcripción y también su parte del índice semántico."],
    ],
    anchos=[4.2, 12.4],
)

imagen("_captura_lector_guia.png", 16.2,
       "Figura 1. Aspecto de la ventana: a la izquierda la descarga y la biblioteca; a la "
       "derecha las pestañas de lectura, consulta y ajustes.")

# ── 5. Leer ──────────────────────────────────
doc.add_heading("5. Leer la transcripción", level=1)
doc.add_paragraph(
    "La pestaña «Transcripción» muestra el título, una línea de datos con el enlace al vídeo "
    "(se abre en tu navegador con un clic) y el texto completo, seleccionable y copiable."
)

doc.add_heading("Tamaño de letra", level=2)
doc.add_paragraph("Tienes tres formas de ajustarlo, y todas recuerdan tu elección entre sesiones:")
vineta("Los botones A− y A+ de la cabecera, con el tamaño actual a la vista (18 pt por defecto).")
vineta("Los atajos Ctrl + =, Ctrl + − y Ctrl + 0 para restablecer (en macOS, la tecla Ctrl "
       "equivale a ⌘).")
vineta("Ctrl + rueda del ratón o del trackpad sobre el texto.")
vineta("En «Ajustes» → Lector tienes el control exacto, de 12 a 40 pt.")
aviso("El lector no está pensado para editar: es un visor. Puedes seleccionar y copiar, pero "
      "no modificar el texto original.")

doc.add_heading("Modo lectura", level=2)
doc.add_paragraph(
    "Para leer de verdad, el lector puede ocupar toda la ventana: pulsa el botón ⛶ de la "
    "fila del lector, la tecla F11 o haz doble clic en una transcripción de la lista. "
    "Desaparecen la lista, la cabecera y el registro, y queda solo el texto. Se sale con "
    "Esc o con el mismo botón."
)
doc.add_paragraph(
    "Dentro del modo lectura aparece el botón ▭: activado limita el ancho de las líneas "
    "(una columna cómoda, centrada); desactivado usa todo el ancho de la ventana. Tú eliges."
)
imagen("_captura_lectura_guia.png", 16.2,
       "Figura 3. Modo lectura con columna cómoda, en una ventana de escritorio.")

doc.add_heading("Ventanas pequeñas y móvil", level=2)
doc.add_paragraph(
    "La interfaz es la misma en un Mac y en una pantalla pequeña: se adapta sola. Por debajo "
    "de unos 600 puntos de ancho, la cabecera se apila, el panel izquierdo pasa encima de las "
    "pestañas y los formularios ponen la etiqueta sobre el campo."
)
vineta("El desplazamiento es global: si la ventana no da de sí, todo el contenido sube y baja.")
vineta("El registro viene oculto; se muestra con el interruptor ▸ / ▾ de su fila y la app "
       "recuerda tu elección.")
vineta("El zoom de letra sigue disponible: A−/A+, Ctrl + rueda y pellizco del trackpad.")

# ── 6. Preguntar ─────────────────────────────
doc.add_heading("6. Preguntar a tus transcripciones", level=1)
doc.add_paragraph(
    "La pestaña «Preguntar» busca en todo tu texto por significado, no por coincidencia de "
    "palabras. Al preguntar, la app recupera los seis pasajes más parecidos y, si hay un "
    "redactor configurado, redacta una respuesta que cita esos pasajes como [1], [2]…"
)
vineta("Pulsa «Indexar» la primera vez. La línea superior te dice cuántos vídeos y pasajes "
       "hay indexados y qué redactor está activo.", "Indexar. ")
vineta("Escribe la pregunta y pulsa «Preguntar» (o Intro). Los pasajes recuperados aparecen "
       "abajo con su puntuación de similitud.", "Preguntar. ")
vineta("Cada cita [n] de la respuesta es un enlace: al pulsarla, se abre la transcripción y "
       "se resalta ese fragmento. Lo mismo si pulsas un pasaje de la lista.", "Citas. ")

imagen("_captura_preguntar_guia.png", 16.2,
       "Figura 2. Una respuesta redactada por el modelo local, con las citas enlazadas y los "
       "seis pasajes recuperados.")

doc.add_heading("Modo recuperación", level=2)
doc.add_paragraph(
    "Si eliges «Sin IA» o si el redactor no responde, la app sigue funcionando: te muestra "
    "los pasajes más relevantes para que los abras tú. Es el modo sin dependencias, útil "
    "cuando no quieres que nada salga de tu equipo."
)

doc.add_heading("Consejos para preguntar bien", level=2)
vineta("Las preguntas concretas funcionan mejor que las genéricas: «¿qué dijo sobre la "
       "telemetría de Windows?» antes que «háblame de Windows».")
vineta("Los nombres propios y las cifras suelen discriminar muy bien entre vídeos.")
vineta("Si responde que el contexto no basta, casi siempre significa que el tema no está en "
       "tus transcripciones: no es un fallo, es que no inventa.")

doc.add_heading("Guardar en el cuaderno (PDF)", level=2)
doc.add_paragraph(
    "Cuando una respuesta te sirva, pulsa «Añadir al cuaderno (PDF)». La app guarda la "
    "pregunta, la respuesta y los pasajes exactos en los que se apoya, y regenera "
    "«cuaderno-<base>.pdf» con todas las preguntas de esa base."
)
vineta("Cada pasaje se imprime con su título y el fragmento literal entre comillas: el mismo "
       "texto que abres al pulsar la cita, no solo un enlace al vídeo.")
vineta("El cuaderno se puede imprimir, anotar o archivar; se regenera desde la base de datos.")
vineta("Si marcas «Abrir PDF al guardar», el visor del sistema se abre con el cuaderno actualizado.")

# ── 7. Redactor ──────────────────────────────
doc.add_heading("7. Elegir la IA que redacta (Ajustes)", level=1)
doc.add_paragraph(
    "En «Ajustes» → Redacción con IA eliges quién escribe la respuesta. La búsqueda "
    "semántica es siempre local; lo único que cambia es el redactor."
)
tabla(
    ["Redactor", "Qué necesita", "Privacidad"],
    [
        ["Sin IA · solo pasajes", "Nada", "Nada sale del equipo"],
        ["Ollama · local", "Ollama instalado y un modelo descargado", "Nada sale del equipo"],
        ["DeepSeek · nube", "Clave API de platform.deepseek.com", "Salen la pregunta y 6 pasajes"],
        ["Otro compatible", "Dirección y modelo de LM Studio, Groq, OpenRouter…", "Según el servicio"],
    ],
    anchos=[4.2, 7.6, 4.8],
)

doc.add_heading("IA local con Ollama, paso a paso", level=2)
vineta("Instala Ollama desde ollama.com y deja la aplicación abierta (o ejecuta «ollama serve»).",
       "1. Instala. ")
vineta("En Terminal: ollama pull qwen2.5:7b-instruct  (unos 4,7 GB; se descarga una sola vez).",
       "2. Descarga un modelo. ")
vineta("En Ajustes elige «Ollama · local», pulsa «Detectar» y elige el modelo en la lista.",
       "3. Selecciona. ")
vineta("Pulsa «Probar conexión»: hace una petición mínima y te dice si responde. Luego «Guardar».",
       "4. Comprueba. ")

aviso("Con 16 GB de RAM, un modelo de 7–8B en cuantización q4 va cómodo (5–6 GB). En un "
      "Apple M2 Pro la primera respuesta tarda unos 20 s (carga el modelo) y después ronda "
      "los 8–13 s. Un modelo de 3–4B es más rápido pero cita peor.")

doc.add_heading("Nube con DeepSeek", level=2)
doc.add_paragraph(
    "Si prefieres no gastar recursos locales, crea una clave en platform.deepseek.com, "
    "pégala en «Clave API» (puedes mostrarla con «Ver»), elige «DeepSeek · nube» y guarda. "
    "Solo se envían al servicio tu pregunta y los seis pasajes recuperados, nunca la base de "
    "datos completa."
)

doc.add_heading("Detectar, guardar y afinar", level=2)
vineta("«Detectar» pregunta al servidor qué modelos tiene instalados y los pone en el "
       "desplegable de «Modelo». Funciona con Ollama, LM Studio y DeepSeek.")
vineta("«Recargar del disco» descarta tus cambios sin guardar y vuelve a leer la configuración.")
vineta("«Temperatura» (0–1,5): más baja, respuestas más literales; más alta, más creativas. "
       "«Máx. tokens» limita la longitud de la respuesta. Los valores por defecto (0,2 y 900) "
       "van bien para citar con fidelidad.")

# ── 8. Datos ─────────────────────────────────
doc.add_heading("8. Dónde están tus datos", level=1)
doc.add_paragraph(
    "Los datos viven fuera de la aplicación, en la carpeta de datos del usuario, para que "
    "puedas actualizar o mover la app sin perder nada:"
)
vineta("macOS: ~/Library/Application Support/BuscadorYT/")
vineta("Windows: %APPDATA%\\BuscadorYT\\")
vineta("Linux: ~/.local/share/BuscadorYT/")
doc.add_paragraph(
    "La primera vez que arranca, la app copia ahí las bases que hubiera junto al ejecutable "
    "(instalación antigua). El menú «Abrir carpeta de datos» te lleva directo."
)
tabla(
    ["Archivo", "Qué contiene"],
    [
        ["<nombre>.db", "Cada tema: transcripciones, índice semántico (fragmentos y vectores) y preguntas guardadas."],
        ["cuaderno-<nombre>.pdf", "El cuaderno de preguntas y respuestas de esa base."],
        ["rag_config.json", "El redactor elegido, su dirección, el modelo y tu clave API si la usas."],
        ["ui_config.json", "Preferencias: tamaño de letra, base activa y si el registro está visible."],
        ["models/", "El modelo de búsqueda (unos 240 MB), descargado en la primera indexación."],
    ],
    anchos=[4.2, 12.4],
)

doc.add_heading("Privacidad", level=2)
vineta("Sin redactor (o con Ollama local) no se envía nada a internet: solo se descargan "
       "subtítulos de YouTube cuando tú lo pides.", "Local. ")
vineta("Con un redactor en la nube salen tu pregunta y los seis pasajes; nunca el resto de "
       "la base de datos.", "Nube. ")
vineta("Copia la carpeta de datos para migrar tu biblioteca a otro equipo.", "Copia de seguridad. ")

# ── 9. Problemas ─────────────────────────────
doc.add_heading("9. Problemas frecuentes", level=1)
tabla(
    ["Qué ves", "Causa", "Solución"],
    [
        ["«YouTube está bloqueando temporalmente tu conexión»",
         "Demasiadas descargas seguidas",
         "Cambia de red o espera 24–48 h; espacia las descargas"],
        ["«No se pudo extraer el ID»",
         "URL incorrecta o incompleta",
         "Pega la dirección completa o el ID de 11 caracteres"],
        ["«El índice está vacío»",
         "Aún no has indexado",
         "Pestaña Preguntar → «Indexar»"],
        ["«RAG no disponible»",
         "Faltan fastembed y numpy",
         "pip install fastembed numpy"],
        ["«No se pudo redactar la respuesta»",
         "Ollama apagado, clave sin configurar o servidor caído",
         "Ajustes → «Probar conexión»; revisa el Registro"],
        ["«Detectar» no encuentra modelos",
         "El servidor no tiene modelos",
         "En Ollama: ollama pull qwen2.5:7b-instruct"],
        ["La primera indexación tarda mucho",
         "Descarga el modelo (240 MB)",
         "Es normal; solo ocurre una vez"],
        ["La primera respuesta tarda ~20 s",
         "Carga del modelo en memoria",
         "Las siguientes tardan 8–13 s"],
        ["«Módulo youtube-transcript-api no encontrado»",
         "Entorno incompleto (versión de desarrollo)",
         "pip install -r requirements.txt"],
    ],
    anchos=[5.2, 5.2, 6.2],
)

# ── 10. Desarrolladores ──────────────────────
doc.add_heading("10. Para quien vaya a mantenerla", level=1)
doc.add_paragraph("Ejecución en desarrollo, desde la carpeta del proyecto:")
tabla(
    ["Tarea", "Comando"],
    [
        ["Instalar dependencias", "python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"],
        ["Abrir la app", ".venv/bin/python BuscadorYT.py"],
        ["Indexar por consola", ".venv/bin/python rag.py index"],
        ["Probar la búsqueda", '.venv/bin/python rag.py search "consulta" -k 6'],
        ["Vista previa por tamaños", ".venv/bin/python preview_responsive.py --tab all --open"],
        ["Compilar .app",
         'PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache" .venv/bin/python -m PyInstaller --clean --noconfirm BuscadorYT.spec'],
    ],
    anchos=[4.6, 12.0],
)

doc.add_heading("Cómo está organizado", level=2)
vineta("BuscadorYT.py: interfaz, base de datos, descarga y exportación a PDF.", "Aplicación. ")
vineta("rag.py: troceado, embeddings, índice, búsqueda y llamada al redactor.", "RAG. ")
vineta("paths.py: carpeta de datos del usuario y migración.", "Datos. ")
vineta("responsive.py: breakpoints, filas adaptativas y flow de botones.", "Interfaz. ")
vineta("BuscadorYT.spec: receta de empaquetado (ejecutable y .app).", "Build. ")
vineta("RAG.md: explicación técnica del índice y de los proveedores de IA.", "Documentación. ")

doc.add_heading("Licencias", level=2)
tabla(
    ["Componente", "Licencia"],
    [
        ["Modelo paraphrase-multilingual-MiniLM-L12-v2", "Apache-2.0 (redistribuible)"],
        ["PySide6 / Qt", "LGPL-3.0"],
        ["reportlab", "BSD"],
        ["youtube-transcript-api", "MIT"],
        ["fastembed / onnxruntime", "Apache-2.0 / MIT"],
        ["numpy", "BSD"],
    ],
    anchos=[8.6, 8.0],
)

cierre = doc.add_paragraph()
cierre.paragraph_format.space_before = Pt(18)
run = cierre.add_run("Con esto deberías poder usar la aplicación de principio a fin. "
                     "Las novedades de cada versión y los detalles técnicos se cuentan en "
                     "RAG.md, dentro de la carpeta del proyecto.")
run.font.size = Pt(10)
run.font.color.rgb = MUTED

doc.save("Guia-de-uso-YT-Transcripts.docx")
print("DOCX generado")
