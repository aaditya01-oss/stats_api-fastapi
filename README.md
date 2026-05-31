## 🚀 Live Demo
**API Docs:** https://statsapi-fastapi-production.up.railway.app/docs

-Deployed on Railway with Docker. Auto-deploys on every push to main via GitHub Actions.
# Stats API

A production-grade statistics REST API built with FastAPI.

## What it does
Send a list of numbers over HTTP and get back:
- Descriptive statistics (mean, median, mode, variance, standard deviation)
- Normal distribution (PDF and CDF)
- Binomial distribution (PMF, mean, variance)
- Poisson distribution (PMF)

## Tech stack
- **FastAPI** — REST API framework
- **Pydantic** — automatic request/response validation
- **pytest** — unit and integration tests
- **Docker** — containerisation
- **GitHub Actions** — CI/CD pipeline

## Project structure
stats-api-fastapi/
├── app/
│   ├── main.py              # entry point
│   ├── routers/stats.py     # HTTP layer
│   └── services/statistics.py  # math logic
├── tests/
│   ├── test_statistics.py   # unit tests
│   └── test_api.py          # integration tests
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

## Run locally

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API documentation.

## Run with Docker

```bash
docker compose up
```

## Run tests

```bash
pytest tests/ -v
```

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /health | Health check |
| POST | /stats/summary | Descriptive statistics |
| POST | /stats/normal | Normal distribution PDF + CDF |
| POST | /stats/binomial | Binomial PMF, mean, variance |
| POST | /stats/poisson | Poisson PMF |
