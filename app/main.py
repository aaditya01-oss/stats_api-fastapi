"""
main.py — Entry point.

Creates the FastAPI application and registers all routers.
This file should stay thin — its only job is wiring things together.
"""

from fastapi import FastAPI
from app.routers.stats import router as stats_router

app = FastAPI(
    title="Stats API",
    description="A production-grade statistics API built with FastAPI.",
    version="1.0.0",
)

# Register the router.
# Now all routes defined in stats.py are live under /stats/*
app.include_router(stats_router)


@app.get("/health")
def health_check():
    """
    GET /health

    A simple endpoint to confirm the server is running.
    Every production API has one — load balancers ping this
    to know if the service is alive.
    """
    return {"status": "ok"}