# RAG en BuscadorYT — búsqueda semántica sobre tus transcripciones

La pestaña **Preguntar** responde preguntas usando *solo* tus transcripciones
guardadas, con citas al pasaje exacto. Todo el índice vive dentro de
`transcripts.db`: no hay servidor vectorial ni servicio externo de búsqueda.

## Cómo funciona

```
transcripts.db ──► chunks (troceado ~900 chars) ──► embeddings locales (ONNX)
                        │                                   │
                        └──────── chunk_vec (float32) ◄──────┘

pregunta ──► embedding ──► coseno top-k ──► 6 pasajes ──► redactor (IA) ──► respuesta [1] [2]
                                │
                                ├─ redactor «Sin IA» → lista de pasajes (modo recuperación)
                                └─ clic en cita → abre la transcripción y resalta el fragmento
```

| Tabla | Contenido |
|---|---|
| `chunks` | fragmentos con `video_id`, orden y offsets `start_char`/`end_char` |
| `chunk_vec` | vector float32 (384 dims) por fragmento, modelo y dimensión |
| `rag_meta` | hash del contenido indexado por vídeo → reindexado incremental |

- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  (fastembed / ONNX, 384 dims, multilingüe). Se descarga **una vez** (~240 MB)
  en `models/` la primera vez que pulsas «Indexar».
- **Indexado incremental:** al descargar o modificar un vídeo solo se procesa ese;
  el resto se reutiliza (hash de contenido + nombre de modelo).
- **Coseno en numpy:** 2.500 fragmentos ≈ 4 MB; consulta en milisegundos.
  Si el corpus crece a >100k fragmentos, el siguiente paso sería `sqlite-vec`
  (tabla virtual `vec0`), sin cambiar el resto del diseño.

## Primer uso

1. `pip install -r requirements.txt` (añade `fastembed` y `numpy`).
2. Abre la app → pestaña **Preguntar** → botón **Indexar**.
   La primera vez descarga el modelo; el resto es local.
3. Escribe la pregunta y pulsa **Preguntar**.

Sin clave API funciona igualmente en **modo recuperación**: te muestra los
pasajes más relevantes, clicables para saltar al texto.

## Redactor: elegir la IA (tab «Ajustes»)

La IA que redacta se elige en la tab **Ajustes** y se guarda en
`rag_config.json` (ignorado por git). Cuatro opciones:

| Redactor | Qué hace |
|---|---|
| **Sin IA · solo pasajes** | Modo recuperación: no sale nada del equipo |
| **DeepSeek · nube** | `api.deepseek.com` + `deepseek-chat`, necesita clave |
| **Ollama · local** | `http://localhost:11434/v1`, todo en el equipo, sin clave |
| **Otro compatible con OpenAI** | LM Studio, llama.cpp, Groq, OpenRouter… |

Los presets viven en `LLM_PROVIDERS` ([BuscadorYT.py](BuscadorYT.py)): añadir un
proveedor es añadir una fila. «Probar conexión» hace una petición mínima antes
de guardar, y **«Detectar»** pregunta al servidor (`GET …/v1/models`) qué modelos
tiene instalados y los pone en el desplegable de «Modelo»: sirve igual para
Ollama, LM Studio o DeepSeek. `rag_config.json` también se puede editar a mano:

```json
{
  "provider": "ollama",
  "base_url": "http://localhost:11434/v1",
  "model": "qwen2.5:7b-instruct",
  "temperature": 0.2,
  "max_tokens": 900
}
```

Con un servidor local (localhost / 127.0.0.1) no hace falta clave. Para la
nube, la clave va en `rag_config.json` (`api_key`) o en la variable
`DEEPSEEK_API_KEY`. Solo se envían al redactor la pregunta y los ~6 pasajes
recuperados (no la base de datos completa).

Modelo local con Ollama:

```bash
ollama pull qwen2.5:7b-instruct
ollama serve
```

## Línea de comandos

```bash
python rag.py index             # indexa solo lo nuevo/cambiado
python rag.py index --reindex   # reconstruye todo (p. ej. tras cambiar de modelo)
python rag.py stats             # vídeos/fragmentos/vectores
python rag.py search "consulta" -k 6
python rag.py ask "pregunta" -k 6            # con LLM si hay clave
python rag.py ask "pregunta" --no-llm        # solo recuperación
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `DEEPSEEK_API_KEY` | clave del redactor (o `rag_config.json` → `api_key`) |
| `FASTEMBED_CACHE_PATH` | carpeta del modelo (por defecto `models/`) |
| `TRANSCRIP_DB` | ruta alternativa de la base de datos |

## Rendimiento medido (M2 Pro, 16 GB)

Con `qwen2.5:7b-instruct` en Ollama y 530 fragmentos indexados:

| Medición | Valor |
|---|---|
| Recuperación (6 pasajes, coseno numpy) | 0,6 s la primera vez · 0,02 s en caliente |
| Redacción, primer arranque (carga el modelo) | ~19 s |
| Redacción en caliente | 8–13 s (60–190 palabras) |
| Memoria del modelo | ~5–6 GB de los 16 GB |

Con temas **fuera** del corpus el modelo responde que el contexto no basta, en
vez de inventar (probado con preguntas sobre vídeos que no están en la BD).

## Limitaciones conocidas

- Las transcripciones antiguas no guardan tiempos de subtítulo: las citas
  apuntan al texto, no a «min 12:34». Para las nuevas habría que conservar los
  segmentos de `youtube-transcript-api` (mejora pendiente).
- No hay búsqueda híbrida BM25 todavía; añadir FTS5 sobre `chunks` mejoraría
  nombres propios y siglas.
- Cambiar de modelo implica reindexar: `rag_meta.model` lo detecta y el botón
  «Indexar» lo hace solo, aunque conviene `--reindex` para limpiar restos.
