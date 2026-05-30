"""
test_api.py — Tests for the HTTP endpoints.

We use FastAPI's TestClient which is built on httpx.
It sends real HTTP requests to your app in memory —
no server running, no ports, no network.

This tests the FULL stack: HTTP → router → service → response.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


# Create one TestClient for all tests in this file.
# This is more efficient than creating a new one per test.
client = TestClient(app)


# ------------------------------------------------------------------
# /health
# ------------------------------------------------------------------

def test_health_check():
    """The health endpoint should always return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ------------------------------------------------------------------
# POST /stats/summary
# ------------------------------------------------------------------

class TestSummaryEndpoint:

    def test_valid_request(self):
        """Standard happy path — valid data, expect 200 and correct mean."""
        response = client.post(
            "/stats/summary",
            json={"numbers": [2, 4, 4, 4, 5, 5, 7, 9]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mean"] == 5.0
        assert data["n"] == 8

    def test_response_has_all_fields(self):
        """Response must contain every field defined in StatsResponse."""
        response = client.post(
            "/stats/summary",
            json={"numbers": [1, 2, 3]}
        )
        assert response.status_code == 200
        data = response.json()
        for field in ["n", "mean", "median", "mode",
                      "population_variance", "sample_variance",
                      "population_std_dev", "sample_std_dev"]:
            assert field in data, f"Missing field: {field}"

    def test_empty_list_rejected(self):
        """
        An empty list should return 422 Unprocessable Entity.
        422 is what FastAPI/Pydantic returns for validation errors.
        """
        response = client.post(
            "/stats/summary",
            json={"numbers": []}
        )
        assert response.status_code == 422

    def test_missing_numbers_field(self):
        """Request body with no 'numbers' key should be rejected."""
        response = client.post(
            "/stats/summary",
            json={"data": [1, 2, 3]}   # wrong key name
        )
        assert response.status_code == 422

    def test_strings_in_list_rejected(self):
        """Strings inside the list should be rejected by Pydantic."""
        response = client.post(
            "/stats/summary",
            json={"numbers": ["a", "b", "c"]}
        )
        assert response.status_code == 422

    def test_single_number(self):
        """A list with one number is valid."""
        response = client.post(
            "/stats/summary",
            json={"numbers": [42]}
        )
        assert response.status_code == 200
        assert response.json()["mean"] == 42.0


# ------------------------------------------------------------------
# POST /stats/normal
# ------------------------------------------------------------------

class TestNormalEndpoint:

    def test_standard_normal_at_zero(self):
        """PDF at x=0 on standard normal should be ~0.3989."""
        response = client.post(
            "/stats/normal",
            json={"x": 0, "mu": 0, "sigma": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pdf"] == pytest.approx(0.3989422804, rel=1e-5)
        assert data["cdf"] == pytest.approx(0.5, rel=1e-5)

    def test_default_mu_and_sigma(self):
        """mu and sigma have defaults — sending just x should work."""
        response = client.post(
            "/stats/normal",
            json={"x": 0}
        )
        assert response.status_code == 200

    def test_invalid_sigma(self):
        """sigma=0 should return 400 Bad Request."""
        response = client.post(
            "/stats/normal",
            json={"x": 0, "mu": 0, "sigma": 0}
        )
        assert response.status_code == 400


# ------------------------------------------------------------------
# POST /stats/binomial
# ------------------------------------------------------------------

class TestBinomialEndpoint:

    def test_valid_request(self):
        response = client.post("/stats/binomial?k=5&n=10&p=0.5")
        assert response.status_code == 200
        data = response.json()
        assert data["pmf"] == pytest.approx(0.24609375, rel=1e-5)
        assert data["mean"] == pytest.approx(5.0)

    def test_invalid_probability(self):
        """p=2.0 is out of range — should return 400."""
        response = client.post("/stats/binomial?k=1&n=5&p=2.0")
        assert response.status_code == 400


# ------------------------------------------------------------------
# POST /stats/poisson
# ------------------------------------------------------------------

class TestPoissonEndpoint:

    def test_valid_request(self):
        response = client.post("/stats/poisson?k=2&lam=3")
        assert response.status_code == 200
        data = response.json()
        assert data["pmf"] == pytest.approx(0.22404180, rel=1e-5)

    def test_invalid_lambda(self):
        """lam=0 should return 400."""
        response = client.post("/stats/poisson?k=1&lam=0")
        assert response.status_code == 400