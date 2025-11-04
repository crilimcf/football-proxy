import os
import logging
import socket
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# ===========================================
# ✅ Forçar IPv4
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
# 🌍 CORS
# ===========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# 🚦 Proxy genérico
# ===========================================
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_request(path: str, request: Request):
    if not API_KEY:
        return Response("❌ API_FOOTBALL_KEY não definida", status_code=500)

    url = f"{TARGET_BASE.rstrip('/')}/{path.lstrip('/')}"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers["x-apisports-key"] = API_KEY
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
        return Response(content=resp.content, status_code=resp.status_code,
                        media_type=resp.headers.get("content-type"))

    except httpx.TimeoutException:
        logging.error("⏳ Timeout ao contactar API-Football.")
        return Response("Timeout contacting API-Football", status_code=504)
    except Exception as e:
        logging.error(f"❌ Erro inesperado no proxy: {e}")
        return Response(f"Proxy error: {e}", status_code=500)

# ===========================================
# 🧠 Health e info
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
        "ip_check": "/ip",
        "ip_test": "/ip/test"
    }

# ===========================================
# 🌍 Endpoint para obter IP público
# ===========================================
@app.get("/ip")
async def get_public_ip():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            ip = (await client.get("https://api.ipify.org")).text
        return {
            "ip_publico": ip,
            "message": "Adiciona este IP na whitelist da API-Football",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        return {"error": f"Não foi possível obter IP público: {e}"}

# ===========================================
# 🧩 Teste de IP autorizado
# ===========================================
@app.get("/ip/test")
async def test_ip_authorization():
    if not API_KEY:
        return {"status": "error", "message": "API_FOOTBALL_KEY não definida"}

    url = f"{TARGET_BASE.rstrip('/')}/status"
    headers = {"x-apisports-key": API_KEY}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)

        data = resp.json()
        if "errors" in data and data["errors"]:
            return {
                "status": "blocked",
                "message": "❌ IP bloqueado — não está na whitelist da API-Football",
                "details": data["errors"]
            }

        return {
            "status": "ok",
            "message": "✅ IP autorizado na API-Football",
            "response": data.get("response", {}),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }

    except Exception as e:
        return {"status": "error", "message": f"Erro ao testar acesso: {e}"}

# ===========================================
# 🚀 Execução local
# ===========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("proxy_apifootball:app", host="0.0.0.0", port=PORT)
