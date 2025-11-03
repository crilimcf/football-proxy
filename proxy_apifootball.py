from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

PROXY_TOKEN = "CF_Proxy_2025_Secret_!@#839"

# --- rota temporária para descobrir o IP público ---
@app.get("/myip")
async def get_my_ip(request: Request):
    return {"ip": request.client.host}
# ----------------------------------------------------

@app.middleware("http")
async def check_token(request: Request, call_next):
    # permite acesso livre apenas ao /myip
    if request.url.path == "/myip":
        return await call_next(request)

    token = request.headers.get("x-proxy-token")
    if token != PROXY_TOKEN:
        return JSONResponse(
            status_code=401,
            content={"detail": "Token inválido ou ausente"},
        )
    return await call_next(request)

@app.get("/status")
async def get_status():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://v3.football.api-sports.io/status",
            headers={"x-apisports-key": "30e1e48fbc6d0839f42212185149c7b4"},
        )
        return r.json()
