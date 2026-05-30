"""
test_statistics.py — Tests for the math service.

We test StatisticsService directly here.
No HTTP, no FastAPI, no server running.
Just: "given this input, do I get this output?"

pytest finds test files automatically if they start with test_
pytest finds test functions automatically if they start with test_
That's the entire naming convention you need to know.
"""

import pytest
from app.services.statistics import StatisticsService


# ------------------------------------------------------------------
# The dataset we'll reuse across multiple tests.
# This is the classic textbook example where std_dev = exactly 2.0
# ------------------------------------------------------------------
SAMPLE_DATA = [2, 4, 4, 4, 5, 5, 7, 9]


# ------------------------------------------------------------------
# Descriptive statistics tests
# ------------------------------------------------------------------

class TestDescriptiveStats:
    """
    Grouping related tests inside a class is optional but clean.
    pytest runs all methods that start with test_ inside it.
    No __init__ needed — pytest handles instantiation.
    """

    def test_mean(self):
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.mean() == 5.0

    def test_median_even_length(self):
        """Even-length list → average of two middle values."""
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.median() == 4.5

    def test_median_odd_length(self):
        """Odd-length list → the exact middle value."""
        svc = StatisticsService([1, 3, 5])
        assert svc.mean() == 3.0

    def test_mode_single(self):
        """4 appears 3 times — it's the only mode."""
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.mode() == [4]

    def test_mode_multimodal(self):
        """Both 1 and 2 appear twice — both are modes."""
        svc = StatisticsService([1, 1, 2, 2, 3])
        assert svc.mode() == [1, 2]

    def test_population_std_dev(self):
        """
        The famous result: std dev of [2,4,4,4,5,5,7,9] = exactly 2.0
        pytest.approx() handles floating point comparison safely.
        Never use == for floats directly — 0.1 + 0.2 != 0.3 in binary.
        """
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.std_dev(population=True) == pytest.approx(2.0)

    def test_sample_std_dev(self):
        """Sample std dev uses N-1, so it's slightly larger than population."""
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.std_dev(population=False) == pytest.approx(2.1380899, rel=1e-5)

    def test_population_variance(self):
        """Variance = std_dev². Population variance = 4.0"""
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.variance(population=True) == pytest.approx(4.0)

    def test_summary_keys(self):
        """
        summary() should return a dict with exactly these keys.
        We test the SHAPE of the output, not just one value.
        """
        svc = StatisticsService(SAMPLE_DATA)
        result = svc.summary()
        expected_keys = {
            "n", "mean", "median", "mode",
            "population_variance", "sample_variance",
            "population_std_dev", "sample_std_dev",
        }
        assert set(result.keys()) == expected_keys

    def test_summary_n(self):
        """n should equal the length of the input."""
        svc = StatisticsService(SAMPLE_DATA)
        assert svc.summary()["n"] == 8

    def test_single_element(self):
        """Edge case: a list with one number."""
        svc = StatisticsService([42.0])
        assert svc.mean() == 42.0
        assert svc.median() == 42.0
        assert svc.mode() == [42.0]


# ------------------------------------------------------------------
# Normal distribution tests
# ------------------------------------------------------------------

class TestNormalDistribution:

    def test_pdf_standard_normal_at_zero(self):
        """
        The peak of the standard normal (mu=0, sigma=1) at x=0.
        Known value: 1 / sqrt(2π) ≈ 0.3989
        """
        result = StatisticsService.normal_pdf(0, mu=0, sigma=1)
        assert result == pytest.approx(0.3989422804, rel=1e-6)

    def test_cdf_at_mean_is_half(self):
        """
        CDF at x=mean should always be exactly 0.5.
        Exactly half the distribution lies below the mean.
        Works for ANY mu and sigma — this is a universal property.
        """
        assert StatisticsService.normal_cdf(0, mu=0, sigma=1) == pytest.approx(0.5)
        assert StatisticsService.normal_cdf(5, mu=5, sigma=2) == pytest.approx(0.5)

    def test_cdf_symmetry(self):
        """
        The normal distribution is symmetric around the mean.
        P(X ≤ mean + d) + P(X ≤ mean - d) should equal 1.0
        """
        cdf_right = StatisticsService.normal_cdf(1, mu=0, sigma=1)
        cdf_left  = StatisticsService.normal_cdf(-1, mu=0, sigma=1)
        assert cdf_right + cdf_left == pytest.approx(1.0)

    def test_pdf_invalid_sigma(self):
        """
        Passing sigma <= 0 should raise a ValueError.
        pytest.raises() is how you test that errors ARE raised correctly.
        If the ValueError is NOT raised, this test FAILS.
        """
        with pytest.raises(ValueError):
            StatisticsService.normal_pdf(0, mu=0, sigma=0)

    def test_pdf_negative_sigma(self):
        with pytest.raises(ValueError):
            StatisticsService.normal_pdf(0, mu=0, sigma=-1)


# ------------------------------------------------------------------
# Binomial distribution tests
# ------------------------------------------------------------------

class TestBinomialDistribution:

    def test_fair_coin_five_heads_in_ten_flips(self):
        """
        Flip a fair coin 10 times. P(exactly 5 heads) ≈ 0.2461
        This is C(10,5) × 0.5^5 × 0.5^5 = 252/1024
        """
        result = StatisticsService.binomial_pmf(k=5, n=10, p=0.5)
        assert result == pytest.approx(0.24609375, rel=1e-6)

    def test_certain_event(self):
        """If p=1.0, P(X=n) must equal 1.0 — it always happens."""
        result = StatisticsService.binomial_pmf(k=5, n=5, p=1.0)
        assert result == pytest.approx(1.0)

    def test_impossible_event(self):
        """If p=0.0, P(X=k) for k>0 must equal 0.0 — never happens."""
        result = StatisticsService.binomial_pmf(k=1, n=5, p=0.0)
        assert result == pytest.approx(0.0)

    def test_invalid_probability(self):
        """p outside [0,1] should raise ValueError."""
        with pytest.raises(ValueError):
            StatisticsService.binomial_pmf(k=1, n=5, p=1.5)

    def test_invalid_k(self):
        """k > n is impossible — should raise ValueError."""
        with pytest.raises(ValueError):
            StatisticsService.binomial_pmf(k=6, n=5, p=0.5)

    def test_mean(self):
        """E[X] = n × p. For n=10, p=0.3: E[X] = 3.0"""
        assert StatisticsService.binomial_mean(10, 0.3) == pytest.approx(3.0)

    def test_variance(self):
        """Var[X] = n × p × (1-p). For n=10, p=0.3: Var = 2.1"""
        assert StatisticsService.binomial_variance(10, 0.3) == pytest.approx(2.1)


# ------------------------------------------------------------------
# Poisson distribution tests
# ------------------------------------------------------------------

class TestPoissonDistribution:

    def test_known_value(self):
        """
        P(X=2 | λ=3) = (3² × e⁻³) / 2! ≈ 0.2240
        Classic textbook value.
        """
        result = StatisticsService.poisson_pmf(k=2, lam=3)
        assert result == pytest.approx(0.22404180, rel=1e-5)

    def test_zero_events(self):
        """
        P(X=0 | λ) = e^(-λ). For λ=1: P(X=0) = e^(-1) ≈ 0.3679
        """
        result = StatisticsService.poisson_pmf(k=0, lam=1)
        assert result == pytest.approx(0.36787944, rel=1e-6)

    def test_invalid_lambda(self):
        """Lambda must be positive — zero makes no sense for a rate."""
        with pytest.raises(ValueError):
            StatisticsService.poisson_pmf(k=1, lam=0)

    def test_negative_k(self):
        """You can't have -1 events."""
        with pytest.raises(ValueError):
            StatisticsService.poisson_pmf(k=-1, lam=2)