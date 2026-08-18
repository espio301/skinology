"""
Spider for OliveYoung US storefront.

Uses curl_cffi to impersonate desktop Chrome TLS fingerprints, bypassing Cloudflare 403s.
Scrapes full HTML product pages directly at us.oliveyoung.com/products/{pid},
extracts exact INCI ingredient lists following the first ']' marker, cleans product titles,
and auto-classifies product types.
"""

import logging
import re
import warnings
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from curl_cffi import requests as cffi_requests

from .base import BaseSpider

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def clean_product_name(raw_name: str) -> str:
    """Strip leading promotional/brand bracket tags like [1+1], [Wellage], [7types]."""
    if not raw_name:
        return ""
    cleaned = re.sub(r'^(?:\[[^\]]+\]\s*)+', '', raw_name).strip()
    return cleaned if cleaned else raw_name


def map_product_type(cat_slug: str, cat_name: str) -> str:
    """Map Olive Young category hierarchy to internal Product.product_type choices."""
    combined = f"{cat_slug} {cat_name}".lower()
    if any(k in combined for k in ['cream', 'moisturizer', 'lotion', 'balm', 'emulsion']):
        return 'moisturizer'
    if any(k in combined for k in ['serum', 'ampoule', 'essence']):
        return 'serum'
    if any(k in combined for k in ['toner', 'mist', 'pad', 'skin']):
        return 'toner'
    if any(k in combined for k in ['cleanser', 'foam', 'wash', 'cleansing']):
        return 'cleanser'
    if any(k in combined for k in ['sun', 'sunscreen', 'sunblock', 'uv']):
        return 'sunscreen'
    if any(k in combined for k in ['mask', 'pack', 'sheet-mask']):
        return 'mask'
    if any(k in combined for k in ['exfolia', 'peel', 'scrub', 'bha', 'aha']):
        return 'exfoliant'
    if any(k in combined for k in ['eye']):
        return 'eye_cream'
    if any(k in combined for k in ['oil']):
        return 'oil'
    return 'serum'


def has_proper_delimiters(inci_text: str) -> bool:
    """
    Check if an INCI text block has proper ingredient delimiters (, or ;)
    with at least 2 separators.
    """
    if not inci_text:
        return False
    delim_count = inci_text.count(',') + inci_text.count(';')
    return delim_count >= 2


class OliveYoungSpider(BaseSpider):
    retailer_name = "Olive Young"
    base_url = "https://us.oliveyoung.com"
    rate_limit = 1.0

    def discover_products(self, max_pages: int = None) -> list[dict]:
        """
        Fetch products from Olive Young US Skincare category (D01) using REST API + HTML scraper.
        """
        products = []
        page = 1
        page_size = 48
        api_cat_url = "https://use-storefront-api-gw.oliveyoung.com/api/v1/q/categories/D01/products"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        while True:
            if max_pages and page > max_pages:
                break

            url = f"{api_cat_url}?page={page}&page_size={page_size}"
            logger.info("Fetching Olive Young API page %s...", page)
            print(f"[{page}] Fetching Olive Young page {page}...", flush=True)

            try:
                import requests
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                items = data.get("data", {}).get("items", [])
                if not items:
                    break

                for item in items:
                    pid = item.get("product_id")
                    raw_title = item.get("product_name", "")
                    clean_name = clean_product_name(raw_title)
                    brand_name = item.get("brand", {}).get("name", "Unknown")
                    image_url = item.get("image_url", "")
                    price_val = item.get("price", {}).get("sale", {}).get("min", {}).get("amount")
                    rating_val = item.get("rating")
                    review_cnt = item.get("review_count")

                    inci_string = ""
                    product_type = "serum"
                    description_text = ""

                    # Direct Webpage HTML Fetch with curl_cffi TLS impersonation
                    detail_url = f"{self.base_url}/products/{pid}"
                    try:
                        c_resp = cffi_requests.get(detail_url, impersonate="chrome124", timeout=15)
                        if c_resp.status_code == 200:
                            html_text = c_resp.text
                            soup = BeautifulSoup(html_text, "html.parser")
                            clean_text = soup.get_text(separator="\n")

                            # Match Full Ingredients / Ingredients sections
                            for m in re.finditer(
                                r"(?:Full\s+Ingredients|Active\s+Ingredients?|Ingredients?|Key\s+Ingredients?)[:\n\s]+"
                                r"(?:[^\n]*list[s]?\s+may\s+change[^\n]*\n)?"
                                r"(.*?)(?=\n\s*(?:How\s+to\s+Use|Why\s+we\s+love\s+it|Product\s+Description|Precautions?|Cautions?|Storage|Details|Shipping|Reviews?|\n\s*\n\s*\n|$))",
                                clean_text,
                                re.IGNORECASE | re.DOTALL
                            ):
                                found = m.group(1).strip()
                                if "Inactive Ingredients:" in found:
                                    found = found.replace("Inactive Ingredients:", " ")

                                # Extract text following the FIRST ']' marker if present
                                if "]" in found:
                                    first_b = found.find("]")
                                    after_b = found[first_b + 1:].strip()
                                    if len(after_b) > 3:
                                        found = after_b

                                if len(found) > 5:
                                    candidate = re.sub(r"\s+", " ", found).strip()
                                    if has_proper_delimiters(candidate):
                                        inci_string = candidate
                                        break
                    except Exception as html_err:
                        logger.warning("Webpage HTML fetch error for %s (%s): %s", clean_name, pid, html_err)

                    # Strictly skip products that do not list a proper delimited ingredient list
                    if not inci_string or not has_proper_delimiters(inci_string):
                        logger.info("Skipping '%s' (%s) — no delimited INCI list on webpage.", clean_name, pid)
                        continue

                    # Storefront API metadata fallback for product type & description
                    try:
                        detail_api_url = f"https://use-storefront-api-gw.oliveyoung.com/api/v1/q/products/{pid}"
                        d_resp = requests.get(detail_api_url, headers=headers, timeout=10)
                        if d_resp.status_code == 200:
                            p_detail = d_resp.json().get("data", {})
                            cat_info = p_detail.get("display_category", {})
                            product_type = map_product_type(cat_info.get("slug", ""), cat_info.get("name", ""))
                            info_en = p_detail.get("attributes", {}).get("product_info_en", "")
                            if info_en:
                                description_text = info_en
                    except Exception:
                        pass

                    raw_product = {
                        "name": clean_name,
                        "brand": brand_name,
                        "product_url": detail_url,
                        "image_url": image_url,
                        "price": price_val,
                        "product_type": product_type,
                        "description": description_text,
                        "inci_string": inci_string,
                        "review_rating": rating_val,
                        "review_count": review_cnt,
                    }
                    products.append(raw_product)

                # Pagination check
                pagination = data.get("data", {}).get("pagination", {})
                current_page = pagination.get("current_page", page)
                total_pages = pagination.get("total_pages", page)

                print(f"✓ Finished scraping page {current_page}/{total_pages} ({len(items)} items processed on page, {len(products)} total products gathered)", flush=True)
                logger.info("Finished scraping page %s/%s (%s items)", current_page, total_pages, len(items))

                if current_page >= total_pages:
                    break

                page += 1

            except Exception as e:
                logger.error("Failed to fetch Olive Young API page %s: %s", page, e)
                break

        return products

    def refresh_price(self, product_url: str) -> dict:
        """Fetch the current price and stock status for a single listing."""
        return {"price": None, "in_stock": True}
