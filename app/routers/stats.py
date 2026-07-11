"""
stats.py — The HTTP layer.

This file's ONLY job is to handle HTTP concerns:
  - What URL does this endpoint live at?
  - What does the incoming request body look like?
  - What does the response look like?
  - Call the service and return the result.

Notice: zero math logic here. If you need to fix a calculation,
you go to services/statistics.py. If you need to change a URL
or add a new endpoint, you come here.
"""

from fastapi import APIRouter, HTTPException, Security
from pydantic import BaseModel, field_validator
from app.services.statistics import StatisticsService
from app.auth import get_current_user


# APIRouter is like a mini FastAPI app.
# You define routes on it, then register it in main.py.
# prefix="/stats" means every route here starts with /stats
router = APIRouter(prefix="/stats", tags=["Statistics"])


# ------------------------------------------------------------------
# Request and Response models (Pydantic)
# ------------------------------------------------------------------

class StatsRequest(BaseModel):
    """
    Defines what the incoming JSON body must look like.

    When a request arrives, Pydantic automatically:
      1. Checks that 'numbers' exists in the JSON
      2. Checks that it's a list
      3. Checks that every item can be converted to a float
      4. Rejects the request with a clear error if anything is wrong

    You don't write any of that validation code yourself.
    """
    numbers: list[float]

    @field_validator("numbers")
    @classmethod
    def must_not_be_empty(cls, v: list[float]) -> list[float]:
        """
        Custom validation rule on top of Pydantic's built-in checks.

        @field_validator runs AFTER Pydantic confirms it's a list of floats.
        This adds our own rule: the list can't be empty.

        cls refers to the class itself (StatsRequest), not an instance.
        v is the value that was passed in for 'numbers'.
        """
        if len(v) == 0:
            raise ValueError("numbers list cannot be empty.")
        return v


class StatsResponse(BaseModel):
    """
    Defines what the JSON response will look like.

    Declaring this explicitly means:
      - Your API has a clear contract — callers know what to expect
      - FastAPI auto-generates documentation for it
      - Pydantic strips out any extra fields you accidentally include
    """
    n: int
    mean: float
    median: float
    mode: list[float]
    population_variance: float
    sample_variance: float
    population_std_dev: float
    sample_std_dev: float


class DistributionRequest(BaseModel):
    """Request model for distribution calculations."""
    x: float
    mu: float = 0.0      # default value: if not provided, use 0.0
    sigma: float = 1.0   # default value: if not provided, use 1.0


class NormalResponse(BaseModel):
    """Response for normal distribution calculations."""
    x: float
    mu: float
    sigma: float
    pdf: float
    cdf: float


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.post("/summary", response_model=StatsResponse)
def get_summary(request: StatsRequest, current_user: str = Security(get_current_user)) -> StatsResponse:
    """
    POST /stats/summary

    Accepts a JSON body like:
        {"numbers": [1, 2, 3, 4, 5]}

    Returns descriptive statistics for the list.

    @router.post means: this handles POST requests.
    response_model=StatsResponse tells FastAPI what the
    response shape is — it uses this for docs and validation.
    """
    svc = StatisticsService(request.numbers)
    result = svc.summary()
    return StatsResponse(**result)
    # **result unpacks the dictionary into keyword arguments:
    # StatsResponse(n=5, mean=3.0, median=3.0, ...)


@router.post("/normal", response_model=NormalResponse)
def get_normal_distribution(request: DistributionRequest, current_user: str = Security(get_current_user)) -> NormalResponse:
    """
    POST /stats/normal

    Accepts: {"x": 1.5, "mu": 0.0, "sigma": 1.0}
    Returns: both PDF and CDF values for that point on the distribution.
    """
    try:
        pdf = StatisticsService.normal_pdf(request.x, request.mu, request.sigma)
        cdf = StatisticsService.normal_cdf(request.x, request.mu, request.sigma)
    except ValueError as e:
        # If the service raises a ValueError (e.g. sigma <= 0),
        # we catch it here and return a proper HTTP 400 error
        # instead of letting the server crash with a 500.
        raise HTTPException(status_code=400, detail=str(e))

    return NormalResponse(
        x=request.x,
        mu=request.mu,
        sigma=request.sigma,
        pdf=pdf,
        cdf=cdf,
    )


@router.post("/binomial")
def get_binomial(k: int, n: int, p: float, current_user: str = Security(get_current_user)):
    """
    POST /stats/binomial?k=3&n=10&p=0.5

    Uses query parameters instead of a request body —
    good for simple inputs with just a few values.

    Returns P(X = k) for a Binomial(n, p) distribution.
    """
    try:
        pmf = StatisticsService.binomial_pmf(k, n, p)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "k": k,
        "n": n,
        "p": p,
        "pmf": pmf,
        "mean": StatisticsService.binomial_mean(n, p),
        "variance": StatisticsService.binomial_variance(n, p),
    }


@router.post("/poisson")
def get_poisson(k: int, lam: float, current_user: str = Security(get_current_user)):
    """
    POST /stats/poisson?k=3&lam=2.5

    Returns P(X = k) for a Poisson(λ) distribution.
    """
    try:
        pmf = StatisticsService.poisson_pmf(k, lam)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"k": k, "lam": lam, "pmf": pmf}