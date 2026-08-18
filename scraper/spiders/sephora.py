"""
Spider for Sephora — sephora.com.

Scrapes skincare product listings and individual product pages for INCI
data, pricing, and stock status.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from .base import BaseSpider

logger = logging.getLogger(__name__)


class SephoraSpider(BaseSpider):
    retailer_name = "Sephora"
    base_url = "https://www.sephora.com"
    rate_limit = 3.0  # Sephora is aggressive with bot detection

    _LISTING_URLS = [
        "https://www.sephora.com/shop/skincare",
    ]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_products(self) -> list[dict]:
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
        soup = self._fetch(product_url)
        if soup is None:
            return {"price": None, "in_stock": False}

        price = self._extract_price(soup)
        in_stock = self._extract_stock_status(soup)
        return {"price": price, "in_stock": in_stock}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_product_links(self, soup: BeautifulSoup) -> list[str]:
        links: list[str] = []
        for a_tag in soup.select("a[href*='/product/']"):
            href = a_tag.get("href", "")
            if href and not href.startswith("http"):
                href = self.base_url.rstrip("/") + href
            if href and href not in links:
                links.append(href)
        return links

    def _scrape_product_page(self, url: str) -> Optional[dict]:
        soup = self._fetch(url)
        if soup is None:
            return None

        name = self._extract_text(soup, "h1")
        brand = self._extract_brand(soup)
        image_url = self._extract_image(soup)
        price = self._extract_price(soup)
        inci_string = self._extract_inci(soup)

        if not name:
            return None

        return {
            "name": name,
            "brand": brand or "Unknown",
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
    def _extract_brand(soup: BeautifulSoup) -> str:
        brand_el = soup.select_one(
            "[data-at='brand_name'], .brand-name, "
            "a[data-comp='BrandName'], span.brand"
        )
        if brand_el:
            return brand_el.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_image(soup: BeautifulSoup) -> str:
        img = soup.select_one(
            "img[data-comp='ProductMainImage'], .product-image img, "
            "img.product-hero"
        )
        if img:
            return img.get("src", "") or img.get("data-src", "")
        return ""

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> Optional[float]:
        price_el = soup.select_one(
            "[data-at='price'], .css-0, span.css-price, "
            ".product-price, span[data-comp='Price']"
        )
        if price_el:
            text = price_el.get_text(strip=True)
            match = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
            if match:
                return float(match.group())
        return None

    @staticmethod
    def _extract_stock_status(soup: BeautifulSoup) -> bool:
        oos = soup.select_one(
            "[data-at='out_of_stock'], .out-of-stock, "
            ".sold-out, button[disabled][data-at='add_to_basket']"
        )
        return oos is None

    @staticmethod
    def _extract_inci(soup: BeautifulSoup) -> str:
        """
        Sephora typically has an ingredients tab or accordion section.
        """
        for section in soup.select(
            "#ingredients, [data-at='ingredients'], "
            ".ingredients-content, .Ingredients"
        ):
            text = section.get_text(separator=", ", strip=True)
            if len(text) > 10:
                return text

        # Fallback: scan for INCI-like content
        for tag in soup.find_all(["p", "div"]):
            text = tag.get_text(strip=True)
            if text and ("Aqua" in text or "Water," in text) and text.count(",") >= 5:
                return text

        return ""
