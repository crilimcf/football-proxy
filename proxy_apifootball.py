import os
import json
import logging
import socket
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ===========================================
# ✅ Forçar IPv4 (evita timeouts em Render)
# ===========================================
orig_getaddrinfo = socket.getaddrinfo
def force_ipv4(*args, **kwargs):
    return [info for info in orig_getaddrinfo(*args, **kwargs) if info[0] == socket.AF_INET]
socket.getaddrinfo = force_ipv4

# ===========================================
# 🔧 Configurações
# ===========================================
API_KEY = os.getenv("API_FOOTBALL_KEY")
TARGET_BASE = "https://v3.football.api-sports.io"
PORT = int(os.getenv("PORT", 10000))
CONFIG_DIR = os.environ.get("CONFIG_DIR", "config")

# ===========================================
# 🧱 Logging
# ===========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI(title="Football Proxy API", version="2.3")

# ===========================================
# 🌍 CORS (permite acesso do frontend e backend)
# ===========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringe se quiseres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# 🔎 Utilitários locais
# ===========================================
def _read_json(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _load_leagues_for(season: str):
    # validação simples da época
    if not (isinstance(season, str) and season.isdigit() and len(season) == 4):
        raise HTTPException(status_code=400, detail="Parâmetro 'season' inválido. Use YYYY (ex.: 2024).")

    path_season = os.path.join(CONFIG_DIR, f"leagues_{season}.json")
    items = _read_json(path_season)

    # fallback para snapshot mais recente
    if not items:
        items = _read_json(os.path.join(CONFIG_DIR, "leagues.json"))

    if not items:
        raise HTTPException(status_code=404, detail=f"Nenhuma lista de ligas encontrada (season={season}).")

    # normalização + ordenação estável
    out = []
    for x in items:
        try:
            out.append({
                "id": int(x["id"]),
                "name": x.get("name"),
                "country": x.get("country"),
                "type": x.get("type"),
            })
        except Exception:
            pass

    # rename amigável (Saudi vem como "Pro League")
    for x in out:
        if (x.get("country") in ("Saudi-Arabia", "Saudi Arabia")) and x.get("name") == "Pro League":
            x["name"] = "Saudi Pro League"

    out.sort(key=lambda y: ((y.get("country") or ""), (y.get("type") or ""), (y.get("name") or "")))
    return out

# ===========================================
# 🌐 Endpoint para ver IP público (whitelist)
# ===========================================
@app.api_route("/ip", methods=["GET", "HEAD"])
async def get_public_ip():
    try:
        async with httpx.AsyncClient() as client:
            ip_publico = (await client.get("https://api.ipify.org")).text.strip()
        return {
            "ip_publico": ip_publico,
            "message": "Adiciona este IP na whitelist da API-Football",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        logging.error(f"Erro ao obter IP público: {e}")
        return {"erro": str(e)}

# ===========================================
# 📚 Leagues (curadas a partir de config/)
# ===========================================
@app.get("/leagues")
@app.get("/meta/leagues")  # alias retro-compatível
def get_leagues(season: str = Query("2024", regex=r"^\d{4}$")):
    return _load_leagues_for(season)

# ===========================================
# 🧠 Health-check e info
# ===========================================
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "football-proxy",
        "version": "2.3",
        "target": TARGET_BASE,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "docs": "/docs",
        "ip_check": "/ip",
        "leagues": "/leagues?season=2024"
    }

# ===========================================
# 🚦 Rota genérica de proxy (deixa NO FIM)
# ===========================================
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_request(path: str, request: Request):
    if not API_KEY:
        return Response("❌ API_FOOTBALL_KEY não definida", status_code=500)

    url = f"{TARGET_BASE.rstrip('/')}/{path.lstrip('/')}"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers["x-apisports-key"] = API_KEY  # substitui sempre por tua chave
    headers.pop("host", None)

    logging.info(f"➡️ Proxying: {url}?{request.query_params}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if request.method == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif request.method == "POST":
                data = await request.body()
                resp = await client.post(url, headers=headers, content=data)
            else:
                return Response("❌ Método não suportado", status_code=405)

        logging.info(f"✅ [{resp.status_code}] {url}")
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

    except httpx.TimeoutException:
        logging.error("⏳ Timeout ao contactar API-Football.")
        return Response("Timeout contacting API-Football", status_code=504)
    except Exception as e:
        logging.error(f"❌ Erro inesperado no proxy: {e}")
        return Response(f"Proxy error: {e}", status_code=500)

# ===========================================
# 🚀 Execução local
# ===========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("proxy_apifootball:app", host="0.0.0.0", port=PORT)
