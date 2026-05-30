"""
statistics.py — The brain of the project.

This file has ZERO FastAPI imports.
It is pure Python math, nothing else.

Why keep it separate?
  1. You can test the math without starting a server
  2. You could swap FastAPI for Flask tomorrow and this file doesn't change
  3. Any bug in the math lives here — easy to find and fix
"""

import math
from collections import Counter


class StatisticsService:
    """
    A class that holds your data and computes stats on it.

    Why a class instead of plain functions?
    - We store the data ONCE in __init__, then compute many things from it
    - We don't recalculate the mean every single time — cleaner code
    - Easy to add more methods later without changing anything else
    """

    def __init__(self, numbers: list[float]) -> None:
        """
        Called when you do: svc = StatisticsService([1, 2, 3])

        The colon syntax is TYPE HINTS — they don't enforce anything at runtime,
        but they tell YOU and your editor what type is expected.
        list[float] means: a list where every item is a float.
        -> None means: this method returns nothing.
        """
        self._data: list[float] = numbers   # underscore = "private, don't touch from outside"
        self._n: int = len(numbers)

    # ------------------------------------------------------------------
    # Descriptive statistics
    # ------------------------------------------------------------------

    def mean(self) -> float:
        """Average: add everything up, divide by count."""
        return sum(self._data) / self._n

    def variance(self, population: bool = True) -> float:
        """
        How spread out the numbers are.

        population=True  → divide by N   (use when you have ALL the data)
        population=False → divide by N-1 (use when your data is a SAMPLE)
        The N-1 version is called Bessel's correction — it gives a less
        biased estimate of the true population variance.

        Edge case: sample variance with n=1 is undefined (division by zero).
        We return 0.0 in that case — a single point has no spread.
        """
        if self._n == 1:
            return 0.0

        mu = self.mean()
        squared_diffs = [(x - mu) ** 2 for x in self._data]
        divisor = self._n if population else (self._n - 1)
        return sum(squared_diffs) / divisor

    def std_dev(self, population: bool = True) -> float:
        """Standard deviation = square root of variance.
        It's in the SAME UNITS as your data, unlike variance (which is units²).
        """
        return math.sqrt(self.variance(population=population))

    def median(self) -> float:
        """
        The middle value when sorted.
        More robust than mean — a single outlier won't move it much.
        """
        sorted_data = sorted(self._data)
        mid = self._n // 2
        if self._n % 2 == 1:
            return sorted_data[mid]
        return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0

    def mode(self) -> list[float]:
        """
        Most frequently occurring value(s).
        Returns a LIST because data can be multimodal (multiple modes).
        Counter({'a': 3, 'b': 2}) counts how many times each value appears.
        """
        counts = Counter(self._data)
        max_count = max(counts.values())
        return sorted(k for k, v in counts.items() if v == max_count)

    def summary(self) -> dict:
        """Returns ALL descriptive stats in one dictionary."""
        return {
            "n": self._n,
            "mean": self.mean(),
            "median": self.median(),
            "mode": self.mode(),
            "population_variance": self.variance(population=True),
            "sample_variance": self.variance(population=False),
            "population_std_dev": self.std_dev(population=True),
            "sample_std_dev": self.std_dev(population=False),
        }

    # ------------------------------------------------------------------
    # Normal distribution
    # ------------------------------------------------------------------

    @staticmethod
    def normal_pdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
        """
        Normal distribution PDF (Probability Density Function).

        @staticmethod means: this method does NOT use self.
        It's attached to the class for organisation, but it's
        really just a function. You call it as:
            StatisticsService.normal_pdf(1.5, mu=0, sigma=1)

        The PDF tells you the RELATIVE LIKELIHOOD of observing value x.
        It's not a probability itself (it can be > 1), but the area
        under the curve between two points IS a probability.

        Formula: (1 / σ√2π) × e^(−½((x−μ)/σ)²)
        """
        if sigma <= 0:
            raise ValueError("sigma must be positive.")
        coefficient = 1.0 / (sigma * math.sqrt(2 * math.pi))
        exponent = -0.5 * ((x - mu) / sigma) ** 2
        return coefficient * math.exp(exponent)

    @staticmethod
    def normal_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
        """
        Normal distribution CDF (Cumulative Distribution Function).

        Answers: "What is P(X ≤ x)?"
        i.e. what fraction of the distribution falls at or below x?

        Uses math.erf (error function) — this is the exact formula,
        no numerical approximation needed.

        Formula: 0.5 × (1 + erf((x − μ) / (σ√2)))
        """
        if sigma <= 0:
            raise ValueError("sigma must be positive.")
        z = (x - mu) / (sigma * math.sqrt(2))
        return 0.5 * (1.0 + math.erf(z))

    # ------------------------------------------------------------------
    # Binomial distribution
    # ------------------------------------------------------------------

    @staticmethod
    def binomial_pmf(k: int, n: int, p: float) -> float:
        """
        Binomial PMF (Probability Mass Function).

        "If I flip a coin n times (each flip has probability p of heads),
         what is the probability of getting EXACTLY k heads?"

        k = number of successes you want to find P for
        n = number of trials
        p = probability of success per trial

        math.comb(n, k) = n! / (k! × (n-k)!) — exact integer arithmetic,
        no floating point error. Python 3.8+ has this built in.

        Formula: C(n,k) × p^k × (1−p)^(n−k)
        """
        if not (0 <= p <= 1):
            raise ValueError("p must be between 0 and 1.")
        if not (0 <= k <= n):
            raise ValueError("k must be between 0 and n.")
        return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    
    @staticmethod
    def binomial_mean(n: int, p: float) -> float:
        """Expected value of Binomial(n, p): E[X] = n × p"""
        return n * p

    @staticmethod
    def binomial_variance(n: int, p: float) -> float:
        """Variance of Binomial(n, p): Var[X] = n × p × (1 − p)"""
        return n * p * (1 - p)

    # ------------------------------------------------------------------
    # Poisson distribution
    # ------------------------------------------------------------------

    @staticmethod
    def poisson_pmf(k: int, lam: float) -> float:
        """
        Poisson PMF.

        "If events happen at an average rate of lam per interval,
         what's the probability of exactly k events in one interval?"

        Examples: k emails per hour, k server requests per second,
        k radioactive decays per minute.

        We use LOG SPACE to avoid overflow:
        Instead of computing lam^k directly (huge for large k),
        we compute k×log(lam) − lam − log(k!) and then exponentiate.
        math.lgamma(k+1) = log(k!) — more numerically stable than math.factorial.

        Formula: (λ^k × e^−λ) / k!
        """
        if lam <= 0:
            raise ValueError("lam (lambda) must be positive.")
        if k < 0:
            raise ValueError("k must be non-negative.")
        log_pmf = k * math.log(lam) - lam - math.lgamma(k + 1)
        return math.exp(log_pmf)