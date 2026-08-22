"""
main.py — AI Firewall entry point.

A FastAPI proxy server that sits between your application
and any LLM API. Every prompt passes through the firewall
before reaching the model.

Endpoints:
  POST /v1/chat     — Main proxy endpoint (intercepts LLM requests)
  GET  /health      — Health check
  GET  /audit       — Recent firewall activity log
  GET  /audit/stats — Summary statistics
  POST /test        — Test a prompt without forwarding to LLM
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.proxy import process_request
from app.logger import init_db, get_recent_logs, get_stats, log_request
from app.scorer import PromptScorer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# After app = FastAPI(...)


app = FastAPI(
    title="AI Firewall",
    description="A proxy server that intercepts LLM requests and blocks prompt injection attacks.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")
# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()
    print("AI Firewall started.")


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class LLMRequest(BaseModel):
    """Flexible request model — accepts any LLM payload format."""
    prompt: str | None = None
    messages: list[dict] | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1000


class TestRequest(BaseModel):
    """Simple request for testing a prompt against the firewall."""
    prompt: str


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Firewall"}


@app.post("/v1/chat")
async def proxy_chat(request: LLMRequest):
    """
    Main proxy endpoint.
    Intercepts the request, scores it, blocks or forwards.
    """
    payload = request.model_dump(exclude_none=True)
    result = await process_request(payload)

    if result.get("blocked"):
        raise HTTPException(
            status_code=403,
            detail=result
        )

    return result


@app.post("/test")
async def test_prompt(request: TestRequest):
    """
    Test endpoint — scores a prompt, logs it, and returns the analysis
    without forwarding to any LLM. Perfect for testing the firewall.
    """
    scorer = PromptScorer(threshold=0.7)
    analysis = scorer.score(request.prompt)
    log_request(analysis)  # ADD THIS LINE
    return analysis


@app.get("/audit")
def audit_log(limit: int = 50):
    """Returns recent firewall activity."""
    return {"logs": get_recent_logs(limit)}


@app.get("/audit/stats")
def audit_stats():
    """Returns summary statistics about firewall activity."""
    return get_stats()