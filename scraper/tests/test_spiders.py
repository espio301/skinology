"""
Tests for retailer spiders.

All tests use mocked HTTP responses — no live network requests are made.
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase
from bs4 import BeautifulSoup

from scraper.spiders.base import BaseSpider
from scraper.spiders.the_ordinary import TheOrdinarySpider


# ---------------------------------------------------------------------------
# Cached HTML fixture helpers
# ---------------------------------------------------------------------------

MOCK_PRODUCT_PAGE_HTML = """
<html>
<head><title>Test Product</title></head>
<body>
    <h1>Niacinamide 10% + Zinc 1%</h1>

    <img class="product-image" src="https://example.com/img/niacinamide.jpg" />

    <span class="product-price">$5.90</span>

    <div id="ingredients">
        Water, Niacinamide, Pentylene Glycol, Zinc PCA, Dimethyl Isosorbide,
        Tamarindus Indica Seed Gum, Xanthan Gum, Isoceteth-20, Ethoxydiglycol,
        Phenoxyethanol, Chlorphenesin
    </div>
</body>
</html>
"""

MOCK_LISTING_PAGE_HTML = """
<html>
<body>
    <a href="/product/niacinamide-10-zinc-1">Niacinamide 10% + Zinc 1%</a>
    <a href="/product/hyaluronic-acid-2-b5">Hyaluronic Acid 2% + B5</a>
    <a href="/other-page">Not a product</a>
</body>
</html>
"""

MOCK_OUT_OF_STOCK_HTML = """
<html>
<body>
    <h1>Out of Stock Product</h1>
    <span class="product-price">$12.00</span>
    <div class="out-of-stock">Out of Stock</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class BaseSpiderFetchTest(TestCase):
    """Tests for ``BaseSpider._fetch`` retry and rate-limiting."""

    def _make_concrete_spider(self):
        """Create a concrete subclass for testing the abstract base."""
        class TestSpider(BaseSpider):
            retailer_name = "TestRetailer"
            base_url = "https://test.example.com"
            rate_limit = 0.01  # almost no delay for tests

            def discover_products(self):
                return []

            def refresh_price(self, product_url):
                return {"price": None, "in_stock": False}

        return TestSpider()

    @patch("scraper.spiders.base.requests.get")
    @patch("scraper.spiders.base.time.sleep")
    def test_successful_fetch_returns_soup(self, mock_sleep, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Hello</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        spider = self._make_concrete_spider()
        soup = spider._fetch("https://test.example.com/page")

        self.assertIsNotNone(soup)
        self.assertEqual(soup.body.text, "Hello")
        mock_get.assert_called_once()
        # Rate-limiting sleep should have been called
        mock_sleep.assert_called()

    @patch("scraper.spiders.base.requests.get")
    @patch("scraper.spiders.base.time.sleep")
    def test_retries_on_500(self, mock_sleep, mock_get):
        import requests as req

        error_response = MagicMock()
        error_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = "<html><body>OK</body></html>"
        success_response.raise_for_status = MagicMock()

        # First call raises 500, second succeeds
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                exc = req.HTTPError(response=error_response)
                raise exc
            return success_response

        mock_get.side_effect = side_effect

        spider = self._make_concrete_spider()
        soup = spider._fetch("https://test.example.com/page")

        self.assertIsNotNone(soup)
        self.assertEqual(mock_get.call_count, 2)

    @patch("scraper.spiders.base.requests.get")
    @patch("scraper.spiders.base.time.sleep")
    def test_returns_none_on_persistent_failure(self, mock_sleep, mock_get):
        import requests as req

        error_response = MagicMock()
        error_response.status_code = 500

        def always_fail(*args, **kwargs):
            raise req.HTTPError(response=error_response)

        mock_get.side_effect = always_fail

        spider = self._make_concrete_spider()
        result = spider._fetch("https://test.example.com/fail", retries=2)

        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 2)


class TheOrdinarySpiderTest(TestCase):
    """Tests for ``TheOrdinarySpider`` against cached HTML."""

    def setUp(self):
        self.spider = TheOrdinarySpider()
        self.spider.rate_limit = 0.01  # fast for tests

    def test_extract_product_links(self):
        soup = BeautifulSoup(MOCK_LISTING_PAGE_HTML, "html.parser")
        links = self.spider._extract_product_links(soup)

        self.assertEqual(len(links), 2)
        self.assertTrue(links[0].endswith("/product/niacinamide-10-zinc-1"))
        self.assertTrue(links[1].endswith("/product/hyaluronic-acid-2-b5"))

    def test_extract_price(self):
        soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")
        price = self.spider._extract_price(soup)

        self.assertEqual(price, 5.90)

    def test_extract_inci(self):
        soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")
        inci = self.spider._extract_inci(soup)

        self.assertIn("Niacinamide", inci)
        self.assertIn("Zinc PCA", inci)

    def test_extract_stock_status_in_stock(self):
        soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")
        self.assertTrue(self.spider._extract_stock_status(soup))

    def test_extract_stock_status_out_of_stock(self):
        soup = BeautifulSoup(MOCK_OUT_OF_STOCK_HTML, "html.parser")
        self.assertFalse(self.spider._extract_stock_status(soup))

    def test_extract_image(self):
        soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")
        image = self.spider._extract_image(soup)

        self.assertEqual(image, "https://example.com/img/niacinamide.jpg")

    @patch.object(TheOrdinarySpider, "_fetch")
    def test_discover_products_uses_links(self, mock_fetch):
        """Integration: listing → product page → structured data."""
        listing_soup = BeautifulSoup(MOCK_LISTING_PAGE_HTML, "html.parser")
        product_soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")

        # First call is the listing page, subsequent calls are product pages
        mock_fetch.side_effect = [listing_soup, product_soup, product_soup]

        products = self.spider.discover_products()

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["brand"], "The Ordinary")
        self.assertEqual(products[0]["name"], "Niacinamide 10% + Zinc 1%")
        self.assertEqual(products[0]["price"], 5.90)

    @patch.object(TheOrdinarySpider, "_fetch")
    def test_refresh_price(self, mock_fetch):
        product_soup = BeautifulSoup(MOCK_PRODUCT_PAGE_HTML, "html.parser")
        mock_fetch.return_value = product_soup

        result = self.spider.refresh_price("https://theordinary.com/product/x")
        self.assertEqual(result["price"], 5.90)
        self.assertTrue(result["in_stock"])
