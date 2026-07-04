"""
main.py — Entry point.

Creates the FastAPI application and registers all routers.
This file should stay thin — its only job is wiring things together.
"""

from fastapi import FastAPI, HTTPException
from app.routers.stats import router as stats_router
from app.auth import LoginRequest, create_access_token

app = FastAPI(
    title="Stats API",
    description="A production-grade statistics API built with FastAPI.",
    version="1.0.0",
)

# Register the router.
# Now all routes defined in stats.py are live under /stats/*
app.include_router(stats_router)


from fastapi import Depends


@app.post("/token")
def login(payload: LoginRequest):
    if payload.username != "admin" or payload.password != "password123":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(payload.username)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/health")
def health_check():
    """
    GET /health

    A simple endpoint to confirm the server is running.
    Every production API has one — load balancers ping this
    to know if the service is alive.
    """
    return {"status": "ok"}