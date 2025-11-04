import os
import logging
import socket
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

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

# ===========================================
# 🧱 Logging
# ===========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI(title="Football Proxy API", version="2.2")

# ===========================================
# 🌍 CORS (permite acesso do frontend e backend)
# ===========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # podes restringir a origem se quiseres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# 🌐 Endpoint para ver IP público (usado no UptimeRobot e whitelist)
# ===========================================
@app.api_route("/ip", methods=["GET", "HEAD"])
async def get_public_ip():
    """
    Retorna o IP público do servidor (para whitelist da API-Football)
    Suporta GET e HEAD (para compatibilidade com UptimeRobot)
    """
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
# 🚦 Rota genérica de proxy
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

        # logging resumo
        logging.info(f"✅ [{resp.status_code}] {url}")
        return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type"))

    except httpx.TimeoutException:
        logging.error("⏳ Timeout ao contactar API-Football.")
        return Response("Timeout contacting API-Football", status_code=504)
    except Exception as e:
        logging.error(f"❌ Erro inesperado no proxy: {e}")
        return Response(f"Proxy error: {e}", status_code=500)

# ===========================================
# 🧠 Health-check e info endpoint
# ===========================================
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "football-proxy",
        "version": "2.2",
        "target": TARGET_BASE,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "docs": "/docs",
        "ip_check": "/ip"
    }

# ===========================================
# 🚀 Execução local
# ===========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("proxy_apifootball:app", host="0.0.0.0", port=PORT)
