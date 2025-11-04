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

app = FastAPI(title="Football Proxy API", version="2.1")

# ===========================================
# 🌍 CORS (acesso liberado)
# ===========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # ou restringe para ["https://previsao-futebol.vercel.app"]
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# 🩺 Health-check
# ===========================================
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# ===========================================
# 🌐 Mostrar IP público do Render
# ===========================================
@app.get("/ip")
async def get_public_ip():
    """
    Retorna o IP público do Render (para whitelist na API-Football)
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            ip = (await client.get("https://api.ipify.org")).text
        return {
            "ip_publico": ip.strip(),
            "message": "Adiciona este IP na whitelist da API-Football",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        logging.error(f"Erro ao obter IP público: {e}")
        return {"erro": str(e)}

# ===========================================
# 🏠 Rota principal
# ===========================================
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "football-proxy",
        "version": "2.1",
        "target": TARGET_BASE,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "docs": "/docs",
        "ip_check": "/ip"
    }

# ===========================================
# 🚦 Rota genérica de proxy
# ===========================================
@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_request(path: str, request: Request):
    # Ignorar endpoints locais
    if path in ["", "healthz", "ip"]:
        return Response("Local route, not proxied.", status_code=400)

    if not API_KEY:
        logging.error("❌ API_FOOTBALL_KEY não definida nas variáveis de ambiente.")
        return Response("❌ API_FOOTBALL_KEY não definida", status_code=500)

    url = f"{TARGET_BASE.rstrip('/')}/{path.lstrip('/')}"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers["x-apisports-key"] = API_KEY
    headers.pop("host", None)

    logging.info(f"➡️ Proxying: {url} | Params: {params}")

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
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json")
        )

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
