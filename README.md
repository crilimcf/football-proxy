# 📘 `football-proxy` — README.md (proposta)

```md
# football-proxy

Proxy **FastAPI** focado em: (1) fixar IP (Render) para **API-Football**; (2) aplicar políticas (rate-limit/cache); (3) simplificar o consumo pelo backend/frontend.

## Rotas
- `GET /health` — healthcheck
- `GET /v3/*` — encaminhamento para API-Football (ex.: `/v3/fixtures?league=39&next=5`)

> Mantém o contrato claro: o proxy **espelha** os endpoints do `/v3/...` e adiciona headers, cache e proteção de quota.

## Variáveis de ambiente
- `APISPORTS_KEY` — **(secreto)** chave da API-Football
- `API_FOOTBALL_BASE` — base upstream (padrão `https://v3.football.api-sports.io/`)
- `ALLOWED_ORIGINS` — CSV com origens permitidas para CORS (ex.: `https://previsao-futebol.onrender.com,http://localhost:3000`)
- `RATE_LIMIT_RPM` — limite de requests/minuto por IP (opcional)

> **Nunca** versiona `.env` neste repo. Usa o painel do Render/GitHub Secrets.

## Desenvolvimento local
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -U pip
pip install -r requirements.txt  # ou pip install -e .
uvicorn app.main:app --reload --port 9000
```

## Testes & Lint
```bash
ruff check .
pytest -q
```

## Deploy (Render)
1) Criar serviço Web (Python) apontando para `uvicorn app.main:app`.
2) Definir envs: `APISPORTS_KEY`, `API_FOOTBALL_BASE`, `ALLOWED_ORIGINS`.
3) Ativar healthcheck em `/health`.
```

---

## ⚙️ CI — GitHub Actions

> CI **mínimo** (lint + test). Ajusta paths conforme a estrutura real do teu repo.

### `previsao-futebol/.github/workflows/ci.yml`
```yaml
name: CI (backend + frontend)

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  python:
    name: Python (lint + test)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f pyproject.toml ]; then pip install .; fi
          pip install ruff pytest

      - name: Ruff (lint)
        run: ruff check .

      - name: Pytest (if tests exist)
        run: |
          if [ -d tests ]; then pytest -q; else echo "No tests/ directory, skipping"; fi

  node:
    name: Frontend (lint + test)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check if frontend exists
        id: has_frontend
        run: |
          if [ -d frontend ] && [ -f frontend/package.json ]; then echo "exists=true" >> $GITHUB_OUTPUT; else echo "exists=false" >> $GITHUB_OUTPUT; fi

      - name: Setup Node
        if: steps.has_frontend.outputs.exists == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install
        if: steps.has_frontend.outputs.exists == 'true'
        working-directory: frontend
        run: npm ci

      - name: ESLint
        if: steps.has_frontend.outputs.exists == 'true'
        working-directory: frontend
        run: |
          if npm run | grep -q "lint"; then npm run lint; else echo "No lint script"; fi

      - name: Tests (if present)
        if: steps.has_frontend.outputs.exists == 'true'
        working-directory: frontend
        run: |
          if npm run | grep -q "test"; then npm test --if-present; else echo "No test script"; fi
```

### `football-proxy/.github/workflows/ci.yml`
```yaml
name: CI (proxy)

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f pyproject.toml ]; then pip install .; fi
          pip install ruff pytest

      - name: Ruff (lint)
        run: ruff check .

      - name: Pytest (if tests exist)
        run: |
          if [ -d tests ]; then pytest -q; else echo "No tests/ directory, skipping"; fi
```

---
