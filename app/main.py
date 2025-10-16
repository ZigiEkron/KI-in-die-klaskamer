# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict
import os, uuid, traceback

# --- load .env BEFORE reading environment variables
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# --- folders
MEDIA_DIR = ROOT_DIR / "media"
WEB_DIR   = ROOT_DIR / "web"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR.mkdir(parents=True, exist_ok=True)

# --- OpenAI client
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY missing.\n"
        f"Create {ROOT_DIR / '.env'} with:\nOPENAI_API_KEY=sk-XXXX\n"
    )
client = OpenAI(api_key=OPENAI_API_KEY)

# --- personas
PERSONA_NAMES: Dict[str, str] = {
    "boer_commando_jan_du_preez": "Jan du Preez",
    "afrikaner_woman_camp_anna_van_der_merwe": "Anna van der Merwe",
    "black_man_with_boers_daniel_kgoathe": "Daniel Kgoathe",
    "british_soldier_arthur_jennings": "Private Arthur Jennings",
}

# --- app
app = FastAPI(title="Boer War Personas Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Optional: no-cache for /ui during dev
@app.middleware("http")
async def no_cache_for_ui(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/ui/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

# ====== models
class ChatInput(BaseModel):
    persona_id: str
    message: str
    tts: bool = True

class ChatOutput(BaseModel):
    reply: str
    audio_url: Optional[str] = None
    avatar: Optional[dict] = None

# ====== helpers
def generate_chat_reply(persona_id: str, message: str) -> str:
    persona_name = PERSONA_NAMES.get(persona_id, "Unknown persona")
    system_prompt = (
        f"You are {persona_name}, a historical persona from the Anglo-Boer War (1899–1902). "
        f"Answer in the first person. For Afrikaans personas, reply in natural early 1900s Afrikaans."
    )
    chat = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )
    return chat.choices[0].message.content.strip()

def synthesize_tts(text: str, persona_id: str) -> Optional[str]:
    voice_map = {
        "boer_commando_jan_du_preez": "onyx",
        "afrikaner_woman_camp_anna_van_der_merwe": "coral",
        "black_man_with_boers_daniel_kgoathe": "alloy",
        "british_soldier_arthur_jennings": "verse",
    }
    voice = voice_map.get(persona_id, "onyx")
    out_path = MEDIA_DIR / f"{uuid.uuid4().hex}.wav"
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text
        ) as response:
            response.stream_to_file(out_path)
        return f"/media/{out_path.name}"
    except Exception as e:
        print("[TTS FAILED]", e)
        traceback.print_exc()
        return None

# ====== routes
@app.post("/chat", response_model=ChatOutput)
def chat_endpoint(inp: ChatInput):
    if inp.persona_id not in PERSONA_NAMES:
        raise HTTPException(status_code=400, detail="Unknown persona_id")
    reply = generate_chat_reply(inp.persona_id, inp.message)
    audio_url = synthesize_tts(reply, inp.persona_id) if inp.tts else None
    return ChatOutput(reply=reply, audio_url=audio_url, avatar=None)

@app.get("/api/status")
def api_status():
    return JSONResponse({"status": "ok", "api": "ready"})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/")
def root():
    return PlainTextResponse("Boer War Personas API is running. Visit /ui/.")

# Debug helpers
@app.get("/_env")
def _env():
    key = os.getenv("OPENAI_API_KEY", "")
    masked = f"{key[:6]}…{key[-4:]}" if key.startswith("sk-") and len(key) > 10 else "(not set/looks odd)"
    return {"OPENAI_API_KEY_present": bool(key), "OPENAI_API_KEY_masked": masked, "env_file": str((ROOT_DIR / '.env').resolve())}

@app.get("/_where")
def _where():
    return {"WEB_DIR_resolved": str(WEB_DIR.resolve()), "ROOT_DIR": str(ROOT_DIR)}

@app.get("/_ls")
def _ls():
    idx = WEB_DIR / "index.html"
    try:
        head = idx.read_text(encoding="utf-8")[:200]
    except Exception as e:
        head = f"ERROR reading {idx}: {e}"
    files = sorted([p.name for p in WEB_DIR.glob('*')])
    return {"web_dir": str(WEB_DIR.resolve()), "files": files, "index_head": head}

# Optional favicon
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    icon = WEB_DIR / "favicon.ico"
    if icon.exists():
        return FileResponse(str(icon))
    return PlainTextResponse("", status_code=204)

# ===== static mounts
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/ui",    StaticFiles(directory=str(WEB_DIR),   html=True), name="web")
