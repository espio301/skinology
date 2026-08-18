"""
Spider for The Ordinary (DECIEM) — theordinary.com.

Scrapes the product listing and individual product pages for INCI data.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from .base import BaseSpider

logger = logging.getLogger(__name__)


class TheOrdinarySpider(BaseSpider):
    retailer_name = "The Ordinary"
    base_url = "https://theordinary.com"
    rate_limit = 2.5  # be polite to DECIEM servers

    # ------------------------------------------------------------------
    # Product listing URL(s) — The Ordinary groups products by regimen
    # ------------------------------------------------------------------
    _LISTING_URLS = [
        "https://theordinary.com/en-us/skincare.html",
    ]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_products(self) -> list[dict]:
        """
        Crawl listing pages and then visit each product page to extract
        INCI data.
        """
        products: list[dict] = []
        seen_urls: set[str] = set()

        for listing_url in self._LISTING_URLS:
            soup = self._fetch(listing_url)
            if soup is None:
                continue

            product_links = self._extract_product_links(soup)
            for link in product_links:
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                product_data = self._scrape_product_page(link)
                if product_data:
                    products.append(product_data)

        logger.info(
            "%s: Discovered %d products", self.retailer_name, len(products)
        )
        return products

    # ------------------------------------------------------------------
    # Price refresh
    # ------------------------------------------------------------------

    def refresh_price(self, product_url: str) -> dict:
        """Fetch current price and stock status from a product page."""
        soup = self._fetch(product_url)
        if soup is None:
            return {"price": None, "in_stock": False}

        price = self._extract_price(soup)
        in_stock = self._extract_stock_status(soup)
        return {"price": price, "in_stock": in_stock}

    # ------------------------------------------------------------------
    # Internal HTML parsing helpers
    # ------------------------------------------------------------------

    def _extract_product_links(self, soup: BeautifulSoup) -> list[str]:
        """Pull product page URLs from a listing page."""
        links: list[str] = []
        for a_tag in soup.select("a[href*='/product/']"):
            href = a_tag.get("href", "")
            if href and not href.startswith("http"):
                href = self.base_url.rstrip("/") + href
            if href and href not in links:
                links.append(href)
        return links

    def _scrape_product_page(self, url: str) -> Optional[dict]:
        """Visit a single product page and extract structured data."""
        soup = self._fetch(url)
        if soup is None:
            return None

        name = self._extract_text(soup, "h1")
        brand = "The Ordinary"  # all products are the same brand
        image_url = self._extract_image(soup)
        price = self._extract_price(soup)
        inci_string = self._extract_inci(soup)

        if not name:
            return None

        return {
            "name": name,
            "brand": brand,
            "product_url": url,
            "image_url": image_url or "",
            "price": price,
            "inci_string": inci_string or "",
        }

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: str) -> str:
        tag = soup.select_one(selector)
        return tag.get_text(strip=True) if tag else ""

    @staticmethod
    def _extract_image(soup: BeautifulSoup) -> str:
        """Try to find the product hero image."""
        img = soup.select_one(
            "img.product-image, img[data-testid='product-image'], "
            ".product-hero img, .product-media img"
        )
        if img:
            return img.get("src", "") or img.get("data-src", "")
        return ""

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> Optional[float]:
        """Parse the price from common price element patterns."""
        price_el = soup.select_one(
            "[data-testid='product-price'], .product-price, "
            ".price, span.money"
        )
        if price_el:
            text = price_el.get_text(strip=True)
            match = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
            if match:
                return float(match.group())
        return None

    @staticmethod
    def _extract_stock_status(soup: BeautifulSoup) -> bool:
        """Check for out-of-stock indicators; default to True."""
        oos = soup.select_one(
            "[data-testid='out-of-stock'], .out-of-stock, "
            ".sold-out, button[disabled]"
        )
        return oos is None

    @staticmethod
    def _extract_inci(soup: BeautifulSoup) -> str:
        """
        Pull the full ingredient / INCI list from the product page.
        The Ordinary often lists ingredients in a section or expandable panel.
        """
        # Strategy 1: look for a dedicated ingredients section
        for section in soup.select(
            "[data-testid='ingredients'], .ingredients-list, "
            "#ingredients, .product-ingredients"
        ):
            text = section.get_text(separator=", ", strip=True)
            if len(text) > 10:
                return text

        # Strategy 2: scan all paragraphs / divs for INCI-like content
        for tag in soup.find_all(["p", "div"]):
            text = tag.get_text(strip=True)
            # INCI lists usually contain "Aqua" or "Water" as the first item
            # and are comma-separated with many entries
            if text and ("Aqua" in text or "Water," in text) and text.count(",") >= 5:
                return text

        return ""
