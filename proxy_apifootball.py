# ==========================================================
# proxy_apifootball.py
# API Football Proxy - by Carlos Fernandes
# ==========================================================

import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
import httpx

# ----------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------
API_KEY = os.getenv("APISPORTS_KEY", "30e1e48fbc6d0839f42212185149c7b4")
BASE_URL = "https://v3.football.api-sports.io"

# Token interno para proteção do proxy (não do API-Football)
PROXY_TOKEN = os.getenv("PROXY_TOKEN", "CF_Proxy_2025_Secret_!@#839")

# ----------------------------------------------------------
# LOGGING
# ----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("proxy")

# ----------------------------------------------------------
# APP
# ----------------------------------------------------------
app = FastAPI(title="Football Proxy API", version="1.0")

# ----------------------------------------------------------
# UTIL
# ----------------------------------------------------------
async def fetch_api(endpoint: str, params: dict = None):
    headers = {"x-apisports-key": API_KEY}
    url = f"{BASE_URL}/{endpoint}"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        log.warning(f"⚠️ API-Football respondeu com {response.status_code}: {response.text}")
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()

# ----------------------------------------------------------
# ENDPOINTS
# ----------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "message": "Football Proxy ativo 🚀"}


@app.get("/status")
async def get_status(request: Request):
    token = request.headers.get("x-proxy-token")
    if token != PROXY_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")

    log.info("🔍 Verificando estado da API...")
    return await fetch_api("status")


@app.get("/fixtures")
async def get_fixtures(request: Request, league: int = None, next: int = None, date: str = None):
    token = request.headers.get("x-proxy-token")
    if token != PROXY_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")

    params = {}
    if league:
        params["league"] = league
    if next:
        params["next"] = next
    if date:
        params["date"] = date

    log.info(f"📅 Fetching fixtures | params={params}")
    return await fetch_api("fixtures", params)


@app.get("/fixtures/next3days")
async def fixtures_next3days(request: Request):
    token = request.headers.get("x-proxy-token")
    if token != PROXY_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")

    results = []
    for i in range(3):
        day = (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d")
        log.info(f"📆 Buscando jogos de {day}")
        day_data = await fetch_api("fixtures", {"date": day})
        results.append({"date": day, "fixtures": day_data.get("response", [])})
    return {"days": results}


@app.get("/myip")
async def myip(request: Request):
    client_ip = request.client.host
    return {"ip": client_ip}

