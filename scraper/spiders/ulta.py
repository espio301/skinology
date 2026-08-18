"""
Spider for Ulta Beauty — ulta.com.

Scrapes skincare product listings and individual product pages for INCI
data, pricing, and stock status.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from .base import BaseSpider

logger = logging.getLogger(__name__)


class UltaSpider(BaseSpider):
    retailer_name = "Ulta"
    base_url = "https://www.ulta.com"
    rate_limit = 2.5

    _LISTING_URLS = [
        "https://www.ulta.com/shop/skin-care",
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
        # Ulta uses productId-based URLs
        for a_tag in soup.select(
            "a[href*='productId='], a[href*='/product/'], "
            ".ProductCard a, .product-listing a"
        ):
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
            ".ProductMainSection__brandName, .product-brand, "
            "a[data-testid='product-brand'], span.brand-name"
        )
        if brand_el:
            return brand_el.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_image(soup: BeautifulSoup) -> str:
        img = soup.select_one(
            "img.ProductHero__image, .product-image img, "
            "img[data-testid='product-image']"
        )
        if img:
            return img.get("src", "") or img.get("data-src", "")
        return ""

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> Optional[float]:
        price_el = soup.select_one(
            ".ProductPricing span, .product-price, "
            "[data-testid='product-price'], span.price"
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
            ".out-of-stock, .sold-out, "
            "button[disabled][data-testid='add-to-bag']"
        )
        return oos is None

    @staticmethod
    def _extract_inci(soup: BeautifulSoup) -> str:
        """
        Ulta typically has an ingredients accordion or tab.
        """
        for section in soup.select(
            "#Ingredients, .ProductDetail__ingredients, "
            "[data-testid='ingredients'], .ingredients"
        ):
            text = section.get_text(separator=", ", strip=True)
            if len(text) > 10:
                return text

        # Fallback
        for tag in soup.find_all(["p", "div"]):
            text = tag.get_text(strip=True)
            if text and ("Aqua" in text or "Water," in text) and text.count(",") >= 5:
                return text

        return ""
