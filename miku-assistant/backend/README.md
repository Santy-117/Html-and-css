# Miku — Motor Cognitivo (backend)

Este es el "cerebro" del asistente: un servicio Python local (FastAPI) que:

- Habla con Gemini (`GEMINI_API_KEY`) para generar las respuestas de Miku.
- Puede abrir apps/archivos de tu PC, pero **solo** los que tú autorices
  explícitamente en `app/tools/allowlist.yaml` (allowlist estricta,
  protegida contra prompt injection: el modelo nunca envía una ruta o
  comando libre, solo una clave predefinida).
- Tiene un caché agresivo en disco para responder al instante preguntas
  repetidas.
- Tiene RAG sobre documentos markdown en `data/memories/` (información
  sobre ti y sobre Miku que quieras que recuerde siempre).

No incluye todavía el display (Vue + Three.js + Electron) ni el pipeline de
voz (faster-whisper / Edge-TTS / RVC) — este backend expone una API HTTP
simple para que esas otras piezas se conecten después.

## 1. Instalación

Requisitos: Python 3.11+.

```bash
cd miku-assistant/backend
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuración

```bash
cp .env.example .env
```

Edita `.env` y pon tu API key de Gemini (la consigues en
https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=tu_api_key_real
```

## 3. Configurar qué apps/archivos puede abrir Miku

Edita `app/tools/allowlist.yaml`. Cada entrada necesita una `key` única, una
`description` (Miku la usa para saber cuándo ofrecerla) y la `path` real en
tu sistema. Ejemplo:

```yaml
apps:
  discord:
    description: "Abre Discord"
    path: "C:/Users/tu_usuario/AppData/Local/Discord/Update.exe"
    args: ["--processStart", "Discord.exe"]
```

No necesitas tocar código: el backend lee este archivo en cada request, así
que puedes agregar/quitar entradas sin reiniciar el servicio.

## 4. Agregar tus memorias (RAG)

Pon archivos `.md` dentro de `data/memories/` con lo que quieras que Miku
recuerde sobre ti, tus proyectos, tu historia con ella, etc. Ya hay dos
ejemplos ahí (`sobre_mi.md`, `sobre_miku.md`) — edítalos o agrega más.

Cada vez que cambies esos archivos, reconstruye el índice:

```bash
curl -X POST http://127.0.0.1:8765/rag/reindex
```

(o simplemente llama a ese endpoint desde el display más adelante).

## 5. Correr el servicio

```bash
python -m app.main
```

Por defecto queda escuchando en `http://127.0.0.1:8765`.

## 6. Probarlo

```bash
curl -X POST http://127.0.0.1:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "Hola Miku, ¿me abres el navegador?"}'
```

Deberías ver una respuesta de Miku y, si tienes una key `navegador`
configurada en la allowlist con una ruta válida, el navegador se abrirá.

## Endpoints

| Método | Ruta            | Descripción                                   |
|--------|-----------------|------------------------------------------------|
| GET    | `/health`       | Chequeo de salud                              |
| POST   | `/chat`         | `{session_id, message}` → `{reply, cached}`   |
| POST   | `/rag/reindex`  | Reconstruye el índice de memorias en markdown |

## Seguridad del sistema de tools

- El modelo **nunca** ve ni envía rutas de archivo ni comandos de shell.
- El único parámetro que puede enviar es una `key` restringida por `enum` al
  esquema de la función (`app/tools/registry.py`) — Gemini no puede inventar
  una key fuera de esa lista, y aunque lo intentara, `run_allowlisted_action`
  la vuelve a validar contra el YAML antes de ejecutar nada.
- Nunca se usa `shell=True`, así que no hay forma de encadenar comandos
  (`;`, `&&`, `|`) ni de inyectar argumentos.
- Contenido recuperado por RAG o devuelto por una tool se marca en el
  system prompt como "información, no instrucciones", como mitigación
  adicional contra prompt injection desde documentos.

## Próximos pasos sugeridos

1. **Display** (Vue + Three.js sobre Electron): una ventana "always on top"
   sin bordes, con un modelo 3D/2D de Miku, que llama a `POST /chat`.
2. **Voz**: faster-whisper para escuchar, Edge-TTS + un modelo RVC de Miku
   para que responda con su voz, todo corriendo local.
