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
client = TestClient(app)


# ------------------------------------------------------------------
# Auth fixture
# Gets a real JWT token once and shares it across all tests
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def auth_headers():
    """
    Logs in once, returns headers with a valid JWT token.
    scope="module" means this runs once per file, not once per test.
    Every test that needs auth just asks for auth_headers.
    """
    response = client.post(
        "/token",
        json={"username": "admin", "password": "password123"}
    )
    assert response.status_code == 200, "Login failed in test setup"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# /health — no auth needed
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

    def test_valid_request(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"numbers": [2, 4, 4, 4, 5, 5, 7, 9]},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mean"] == 5.0
        assert data["n"] == 8

    def test_response_has_all_fields(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"numbers": [1, 2, 3]},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for field in ["n", "mean", "median", "mode",
                      "population_variance", "sample_variance",
                      "population_std_dev", "sample_std_dev"]:
            assert field in data, f"Missing field: {field}"

    def test_empty_list_rejected(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"numbers": []},
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_missing_numbers_field(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"data": [1, 2, 3]},
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_strings_in_list_rejected(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"numbers": ["a", "b", "c"]},
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_single_number(self, auth_headers):
        response = client.post(
            "/stats/summary",
            json={"numbers": [42]},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["mean"] == 42.0


# ------------------------------------------------------------------
# POST /stats/normal
# ------------------------------------------------------------------

class TestNormalEndpoint:

    def test_standard_normal_at_zero(self, auth_headers):
        response = client.post(
            "/stats/normal",
            json={"x": 0, "mu": 0, "sigma": 1},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pdf"] == pytest.approx(0.3989422804, rel=1e-5)
        assert data["cdf"] == pytest.approx(0.5, rel=1e-5)

    def test_default_mu_and_sigma(self, auth_headers):
        response = client.post(
            "/stats/normal",
            json={"x": 0},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_invalid_sigma(self, auth_headers):
        response = client.post(
            "/stats/normal",
            json={"x": 0, "mu": 0, "sigma": 0},
            headers=auth_headers
        )
        assert response.status_code == 400


# ------------------------------------------------------------------
# POST /stats/binomial
# ------------------------------------------------------------------

class TestBinomialEndpoint:

    def test_valid_request(self, auth_headers):
        response = client.post(
            "/stats/binomial?k=5&n=10&p=0.5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pmf"] == pytest.approx(0.24609375, rel=1e-5)
        assert data["mean"] == pytest.approx(5.0)

    def test_invalid_probability(self, auth_headers):
        response = client.post(
            "/stats/binomial?k=1&n=5&p=2.0",
            headers=auth_headers
        )
        assert response.status_code == 400


# ------------------------------------------------------------------
# POST /stats/poisson
# ------------------------------------------------------------------

class TestPoissonEndpoint:

    def test_valid_request(self, auth_headers):
        response = client.post(
            "/stats/poisson?k=2&lam=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pmf"] == pytest.approx(0.22404180, rel=1e-5)

    def test_invalid_lambda(self, auth_headers):
        response = client.post(
            "/stats/poisson?k=1&lam=0",
            headers=auth_headers
        )
        assert response.status_code == 400