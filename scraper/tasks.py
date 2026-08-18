"""
Celery tasks for SkinStudy's data pipeline.

These tasks are auto-discovered by the Celery app configured in
``backend/celery.py`` and can be scheduled via ``django-celery-beat``.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def discover_new_products(self):
    """
    Daily task: run all registered spiders to find new products.

    For each product discovered:
      1. Parse its INCI list → canonical ingredient names.
      2. Match or create ``Ingredient`` records.
      3. Create the ``Product`` (if new) and ``ProductIngredient`` links.
      4. Create / update the ``RetailerListing``.
      5. Auto-tag skin concerns.
    """
    from api.models import Product, ProductIngredient, Retailer, RetailerListing
    from scraper.parsers import parse_inci_list, match_or_create_ingredients
    from scraper.spiders import SPIDER_REGISTRY
    from scraper.taggers import auto_tag_product

    total_new = 0
    total_updated = 0

    for retailer_name, SpiderClass in SPIDER_REGISTRY.items():
        spider = SpiderClass()
        logger.info("Running spider: %s", retailer_name)

        try:
            raw_products = spider.discover_products()
        except Exception as exc:
            logger.error("Spider %s failed: %s", retailer_name, exc)
            continue

        # Ensure the retailer exists
        retailer, _ = Retailer.objects.get_or_create(
            name=retailer_name,
            defaults={"base_url": spider.base_url},
        )

        for raw in raw_products:
            try:
                product, created = _upsert_product(raw)

                # Parse and link ingredients
                if raw.get("inci_string"):
                    inci_names = parse_inci_list(raw["inci_string"])
                    ingredients = match_or_create_ingredients(inci_names)
                    _link_ingredients(product, ingredients)
                    product.raw_inci = inci_names
                    product.save(update_fields=["raw_inci"])
                    
                    if "ingredient_functions" in raw:
                        _upsert_ingredient_functions(ingredients, raw["ingredient_functions"])
                        
                    _scrape_ingredient_proofs_if_needed(spider, ingredients)

                # Upsert retailer listing
                _upsert_listing(product, retailer, raw)

                # Auto-tag concerns
                auto_tag_product(product)

                if created:
                    total_new += 1
                else:
                    total_updated += 1

            except Exception as exc:
                logger.error(
                    "Error processing product '%s': %s",
                    raw.get("name", "?"), exc,
                )

    logger.info(
        "discover_new_products complete — %d new, %d updated",
        total_new, total_updated,
    )
    return {"new": total_new, "updated": total_updated}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_prices(self):
    """
    Runs 2x/day: refresh price and stock status for every existing listing.
    """
    from api.models import RetailerListing
    from scraper.spiders import SPIDER_REGISTRY

    updated = 0
    errors = 0

    # Build a reverse lookup: retailer name → spider instance
    spider_instances = {
        name: cls() for name, cls in SPIDER_REGISTRY.items()
    }

    listings = RetailerListing.objects.select_related("retailer").all()

    for listing in listings:
        spider = spider_instances.get(listing.retailer.name)
        if spider is None:
            continue

        try:
            result = spider.refresh_price(listing.product_url)
            changed = False

            if result.get("price") is not None and result["price"] != listing.price:
                listing.price = result["price"]
                changed = True

            if result.get("in_stock") != listing.in_stock:
                listing.in_stock = result["in_stock"]
                changed = True

            if changed:
                listing.save(update_fields=["price", "in_stock", "last_scraped"])
                updated += 1

        except Exception as exc:
            logger.error(
                "Error refreshing price for listing %s: %s", listing.pk, exc,
            )
            errors += 1

    logger.info(
        "refresh_prices complete — %d updated, %d errors", updated, errors,
    )
    return {"updated": updated, "errors": errors}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_single_product(self, product_url: str, retailer_name: str):
    """
    On-demand task: import a single product by URL and retailer.

    Useful for manual admin imports or adding a product that was missed
    during discovery.
    """
    from api.models import Retailer
    from scraper.parsers import parse_inci_list, match_or_create_ingredients
    from scraper.spiders import SPIDER_REGISTRY
    from scraper.taggers import auto_tag_product

    SpiderClass = SPIDER_REGISTRY.get(retailer_name)
    if SpiderClass is None:
        raise ValueError(f"Unknown retailer: {retailer_name}")

    spider = SpiderClass()
    soup = spider._fetch(product_url)
    if soup is None:
        raise RuntimeError(f"Failed to fetch {product_url}")

    # Use the spider's internal page scraper
    raw = spider._scrape_product_page(product_url)
    if raw is None:
        raise RuntimeError(f"Failed to parse product page: {product_url}")

    retailer, _ = Retailer.objects.get_or_create(
        name=retailer_name,
        defaults={"base_url": spider.base_url},
    )

    product, created = _upsert_product(raw)

    if raw.get("inci_string"):
        inci_names = parse_inci_list(raw["inci_string"])
        ingredients = match_or_create_ingredients(inci_names)
        _link_ingredients(product, ingredients)
        product.raw_inci = inci_names
        product.save(update_fields=["raw_inci"])
        
        if "ingredient_functions" in raw:
            _upsert_ingredient_functions(ingredients, raw["ingredient_functions"])
            
        _scrape_ingredient_proofs_if_needed(spider, ingredients)

    _upsert_listing(product, retailer, raw)
    auto_tag_product(product)

    action = "created" if created else "updated"
    logger.info("process_single_product: %s %s", action, product)
    return {"product_id": product.pk, "action": action}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upsert_product(raw: dict):
    """Create or update a Product from a raw spider dict."""
    from api.models import Product

    defaults = {
        "image_url": raw.get("image_url", ""),
        "description": raw.get("description", ""),
    }
    if raw.get("product_type"):
        defaults["product_type"] = raw["product_type"]

    product, created = Product.objects.get_or_create(
        name=raw["name"],
        brand=raw["brand"],
        defaults=defaults,
    )

    updated_fields = []
    if not created:
        if raw.get("image_url") and not product.image_url:
            product.image_url = raw["image_url"]
            updated_fields.append("image_url")
        if raw.get("description") and not product.description:
            product.description = raw["description"]
            updated_fields.append("description")
        if raw.get("product_type") and product.product_type == "other":
            product.product_type = raw["product_type"]
            updated_fields.append("product_type")
        if updated_fields:
            product.save(update_fields=updated_fields)

    return product, created


def _link_ingredients(product, ingredients, concentration_map=None):
    """Create ProductIngredient through-model entries preserving INCI order."""
    from api.models import ProductIngredient

    concentration_map = concentration_map or {}

    existing = set(
        ProductIngredient.objects.filter(product=product)
        .values_list("ingredient_id", flat=True)
    )

    for order, ingredient in enumerate(ingredients, start=1):
        if ingredient.pk in existing:
            continue
        existing.add(ingredient.pk)

        conc_str = concentration_map.get(ingredient.inci_name, "")
        ProductIngredient.objects.create(
            product=product,
            ingredient=ingredient,
            order=order,
            concentration=conc_str,
        )


def _upsert_listing(product, retailer, raw: dict):
    """Create or update a RetailerListing."""
    from api.models import RetailerListing

    listing, created = RetailerListing.objects.update_or_create(
        product=product,
        retailer=retailer,
        defaults={
            "price": raw.get("price"),
            "product_url": raw.get("product_url", ""),
            "in_stock": True,
        },
    )
    return listing, created


def _upsert_ingredient_functions(ingredients, ingredient_functions):
    """Map scraped key ingredient functions to SkinConcern tags internally."""
    from api.models import SkinConcern
    from scraper.parsers.synonym_table import resolve_synonym
    from django.utils.text import slugify
    
    canonical_map = {ing.inci_name.lower(): ing for ing in ingredients}
    
    for raw_name, func_list in ingredient_functions.items():
        canonical = resolve_synonym(raw_name)
        ing = canonical_map.get(canonical.lower())
        if not ing:
            continue
            
        for func in func_list:
            slug = slugify(func)
            concern, _ = SkinConcern.objects.get_or_create(
                internal_key=slug,
                defaults={'label': func}
            )
            ing.concerns_supported.add(concern)


_scraped_proofs_cache = set()

def _scrape_ingredient_proofs_if_needed(spider, ingredients):
    """Optionally fetch and parse 'Show me some proof' articles for valid ingredients."""
    from api.models import Article
    from django.utils.text import slugify

    # Optimization: If the spider cannot do it, bypass
    if not hasattr(spider, 'scrape_ingredient_page'):
        return

    for ing in ingredients:
        if ing.inci_name in _scraped_proofs_cache or ing.articles.exists():
            continue
            
        _scraped_proofs_cache.add(ing.inci_name)
        slug = slugify(ing.common_name or ing.inci_name)
        try:
            data = spider.scrape_ingredient_page(slug)
            proofs = data.get("proofs", [])
            for proof in proofs:
                title = proof[:500] if len(proof) > 500 else proof
                article, _ = Article.objects.get_or_create(
                    title=title,
                    defaults={'url': None, 'summary': proof}
                )
                article.ingredients.add(ing)
        except Exception as e:
            logger.error("Failed to scrape proofs for %s: %s", ing.inci_name, e)
