import os
import sys

# Ensure virtual environment packages are accessible
venv_site_packages = os.path.join(os.path.dirname(__file__), '.venv', 'lib', 'python3.9', 'site-packages')
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Product, Ingredient, Article, SkinConcern, RetailerListing
from scraper.spiders.oliveyoung import OliveYoungSpider
from scraper.tasks import _upsert_product, _upsert_listing

print("Wiping database...")
Product.objects.all().delete()
Ingredient.objects.all().delete()
Article.objects.all().delete()
# Keep SkinConcern objects intact so taxonomy remains in database
RetailerListing.objects.all().delete()
print("Database wiped (concerns preserved).")

from django.core.management import call_command
print("Seeding base ingredients and products...")

print("Instantiating Olive Young Spider...")
spider = OliveYoungSpider()
print("Scraping Olive Young products...")
from api.models import Retailer
retailer, _ = Retailer.objects.get_or_create(
    name=spider.retailer_name,
    defaults={"base_url": spider.base_url},
)

# Parse optional CLI argument for max_pages
max_pages = None
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    max_pages = int(sys.argv[1])
    print(f"Scraping Olive Young products (limit: {max_pages} pages)...")
else:
    print("Scraping Olive Young products across ALL pages...")

raw_products = spider.discover_products(max_pages=max_pages)
print(f"Discovered {len(raw_products)} products.")

from scraper.parsers.inci_parser import parse_inci_list, match_or_create_ingredients
from scraper.spiders.oliveyoung import has_proper_delimiters
from scraper.tasks import _link_ingredients
from scraper.taggers import auto_tag_product

print("Inserting into database...")
for raw in raw_products:
    if not raw.get("inci_string") or not has_proper_delimiters(raw["inci_string"]):
        print(f"Skipping product '{raw.get('name')}' — no proper delimited ingredient list.")
        continue

    product, created = _upsert_product(raw)
    _upsert_listing(product, retailer, raw)
    
    # Store review rating and count correctly
    if 'review_rating' in raw:
        product.review_rating = raw['review_rating']
    if 'review_count' in raw:
        product.review_count = raw['review_count']
    product.save(update_fields=['review_rating', 'review_count'])
    
    if raw.get("inci_string"):
        from scraper.parsers.inci_parser import extract_active_concentrations
        conc_map = extract_active_concentrations(raw["inci_string"])
        inci_names = parse_inci_list(raw["inci_string"])
        ingredients = match_or_create_ingredients(inci_names)
        _link_ingredients(product, ingredients, concentration_map=conc_map)
        product.raw_inci = inci_names
        product.save(update_fields=["raw_inci"])
        
    # Auto-tag skin concerns based on linked ingredients
    auto_tag_product(product)

print(f"Done! {Product.objects.count()} products now in database.")

print("Running ingredient extractor for products missing INCI lists...")
import fix_missing_ingredients
fix_missing_ingredients.run()

print("Seeding PubMed terms & syncing ingredient umbrellas and concerns...")
call_command("seed_pubmed_terms")
call_command("sync_ingredient_umbrellas")
call_command("sync_ingredient_concerns")

print("Estimating product pH and strength classifications...")
call_command("estimate_product_attributes")
print("Wipe, scrape, ingredient sync, and attribute estimation complete!")
