"""
Abstract base class for all retailer spiders.

Subclasses implement ``discover_products()`` and ``refresh_price()`` for a
specific retailer.  The base class provides HTTP fetching with retries,
rate-limiting, and a rotating user-agent pool.
"""

import abc
import logging
import random
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Realistic desktop user-agents to reduce bot-detection risk.
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0",
]

# Default seconds to sleep between requests to the same domain.
DEFAULT_RATE_LIMIT = 2.0

# Maximum number of retries for a single HTTP request.
MAX_RETRIES = 3


class BaseSpider(abc.ABC):
    """
    Abstract spider that specific retailer spiders extend.

    Attributes:
        retailer_name: Human-readable name matching a ``Retailer.name``.
        base_url: Root URL of the retailer website.
        rate_limit: Seconds to sleep between requests (jittered ±25 %).
    """

    retailer_name: str = ""
    base_url: str = ""
    rate_limit: float = DEFAULT_RATE_LIMIT

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def discover_products(self) -> list[dict]:
        """
        Crawl the retailer site and return a list of raw product dicts.

        Each dict must contain at minimum::

            {
                "name": str,
                "brand": str,
                "product_url": str,
                "image_url": str,        # may be ""
                "price": float | None,
                "inci_string": str,      # comma-separated INCI list
            }
        """

    @abc.abstractmethod
    def refresh_price(self, product_url: str) -> dict:
        """
        Fetch the current price and stock status for a single listing.

        Returns::

            {"price": float | None, "in_stock": bool}
        """

    # ------------------------------------------------------------------
    # Shared HTTP helper
    # ------------------------------------------------------------------

    def _fetch(self, url: str, *, retries: int = MAX_RETRIES) -> Optional[BeautifulSoup]:
        """
        GET *url* and return parsed ``BeautifulSoup``, or ``None`` on failure.

        * Picks a random user-agent each call.
        * Retries up to *retries* times on transient HTTP errors (5xx).
        * Sleeps ``self.rate_limit`` ±25 % between requests.
        """
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                # Rate-limit: sleep with ±25 % jitter
                jitter = self.rate_limit * random.uniform(0.75, 1.25)
                time.sleep(jitter)
                return BeautifulSoup(resp.text, "html.parser")
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else 0
                if 500 <= status < 600 and attempt < retries:
                    wait = 2 ** attempt + random.random()
                    logger.warning(
                        "%s: %s returned %s — retrying in %.1fs (attempt %d/%d)",
                        self.retailer_name, url, status, wait, attempt, retries,
                    )
                    time.sleep(wait)
                    continue
                logger.error(
                    "%s: Failed to fetch %s — HTTP %s",
                    self.retailer_name, url, status,
                )
                return None
            except requests.RequestException as exc:
                logger.error(
                    "%s: Request error for %s — %s",
                    self.retailer_name, url, exc,
                )
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                return None

        return None  # should not reach here, but satisfies type checker
