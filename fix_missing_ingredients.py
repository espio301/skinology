import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

import re
import requests
from bs4 import BeautifulSoup
from api.models import Product, RetailerListing

from scraper.parsers.inci_parser import parse_inci_list, match_or_create_ingredients
from scraper.tasks import _link_ingredients

def run():
    # Only pick products from Olive Young that are missing ingredients
    query = Product.objects.filter(
        retailer_listings__retailer__name='Olive Young', 
        product_ingredients__isnull=True
    ).distinct()

    count = query.count()
    print(f"Found {count} Olive Young products missing ingredients.")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    success = 0

    for i, prod in enumerate(query):
        listing = RetailerListing.objects.filter(product=prod).first()
        if not listing or not listing.product_url:
            continue

        try:
            from curl_cffi import requests as cffi_requests
            resp = cffi_requests.get(listing.product_url, impersonate="chrome124", timeout=15)
            if resp.status_code == 200:
                html_text = resp.text
                if "ingredient" in html_text.lower():
                    soup = BeautifulSoup(html_text, "html.parser")
                    clean_text = soup.get_text(separator="\n")
                    
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
                            if "," in candidate or ";" in candidate or "water" in candidate.lower() or "extract" in candidate.lower():
                                inci_string = candidate
                                break

                if not inci_string and "__NEXT_DATA__" in html_text:
                    try:
                        import json
                        next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text, re.DOTALL)
                        if next_data_match:
                            data_json = json.loads(next_data_match.group(1))
                            json_str = json.dumps(data_json)
                            ing_match = re.search(r'["\'](?:Full\s+)?Ingredients["\']\s*:\s*["\']([^"\']+)["\']', json_str, re.IGNORECASE)
                            if ing_match:
                                inci_string = ing_match.group(1).strip()
                    except Exception:
                        pass

            from scraper.spiders.oliveyoung import has_proper_delimiters
            if not inci_string or not has_proper_delimiters(inci_string):
                continue

            from scraper.parsers.inci_parser import extract_active_concentrations
            conc_map = extract_active_concentrations(inci_string)
            inci_names = parse_inci_list(inci_string)
            if inci_names:
                import time
                from django.db import transaction, OperationalError
                
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        with transaction.atomic():
                            ingredients = match_or_create_ingredients(inci_names)
                            _link_ingredients(prod, ingredients, concentration_map=conc_map)
                            prod.raw_inci = inci_names
                            prod.save(update_fields=["raw_inci"])
                        success += 1
                        if success % 10 == 0:
                            print(f"Successfully added ingredients for {success} products...")
                        break
                    except OperationalError as dbe:
                        if "locked" in str(dbe).lower() and attempt < max_retries - 1:
                            time.sleep(0.5)
                        else:
                            print(f"Error for {prod.name}: {dbe}")
                            break
                            
                            
        except Exception as e:
            print(f"Error for {prod.name}: {e}")

    print(f"Finished. Extracted ingredients for {success} out of {count} previously missing products.")

if __name__ == '__main__':
    run()
