"""
Management command to seed the database with curated skincare products.

Usage::

    python manage.py seed_products          # seed all data
    python manage.py seed_products --clear  # wipe and re-seed
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import (
    Ingredient, IngredientUmbrella, Product, ProductIngredient,
    Retailer, RetailerListing, SkinConcern,
)
from scraper.parsers import parse_inci_list, match_or_create_ingredients
from scraper.taggers import auto_tag_product
from scraper.data.seed_products import SEED_PRODUCTS, SKIN_CONCERNS, CONCERN_INGREDIENT_MAP


class Command(BaseCommand):
    help = "Seed the database with curated skincare products, ingredients, and concerns."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing products, ingredients, and concerns before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            ProductIngredient.objects.all().delete()
            RetailerListing.objects.all().delete()
            Product.objects.all().delete()
            Ingredient.objects.all().delete()
            IngredientUmbrella.objects.all().delete()
            SkinConcern.objects.all().delete()
            Retailer.objects.all().delete()

        self._seed_concerns()
        self._seed_retailers()
        new_count, skip_count = self._seed_products()
        self._map_concerns_to_ingredients()
        tagged = self._auto_tag_all()

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {new_count} products created, {skip_count} skipped (existing). "
            f"{tagged} products auto-tagged with concerns."
        ))

    def _seed_concerns(self):
        for label, key in SKIN_CONCERNS:
            obj, created = SkinConcern.objects.get_or_create(
                internal_key=key, defaults={"label": label},
            )
            if created:
                self.stdout.write(f"  + Concern: {label}")

    def _seed_retailers(self):
        retailers = [
            ("The Ordinary", "https://theordinary.com", "direct"),
            ("Sephora", "https://www.sephora.com", "sovrn"),
            ("Ulta", "https://www.ulta.com", "sovrn"),
            ("Amazon", "https://www.amazon.com", "amazon_associates"),
            ("CeraVe", "https://www.cerave.com", "direct"),
            ("Paula's Choice", "https://www.paulaschoice.com", "sovrn"),
        ]
        for name, url, network in retailers:
            Retailer.objects.get_or_create(
                name=name, defaults={"base_url": url, "affiliate_network": network},
            )

    def _seed_products(self):
        new_count = 0
        skip_count = 0

        for item in SEED_PRODUCTS:
            name = item["name"]
            brand = item["brand"]

            if Product.objects.filter(name=name, brand=brand).exists():
                skip_count += 1
                continue

            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    brand=brand,
                    description=item.get("description", ""),
                    product_type=item.get("product_type", "other"),
                    image_url=item.get("image_url", ""),
                )

                inci_string = item.get("ingredients", "")
                if inci_string:
                    inci_names = parse_inci_list(inci_string)
                    ingredients = match_or_create_ingredients(inci_names)
                    for order, ing in enumerate(ingredients, 1):
                        ProductIngredient.objects.get_or_create(
                            product=product, ingredient=ing,
                            defaults={"order": order},
                        )
                    product.raw_inci = inci_names
                    product.save(update_fields=["raw_inci"])

                # Create a retailer listing if price is provided
                price = item.get("price")
                retailer_name = item.get("retailer", brand)
                if price:
                    retailer = Retailer.objects.filter(name=retailer_name).first()
                    if retailer:
                        RetailerListing.objects.get_or_create(
                            product=product, retailer=retailer,
                            defaults={
                                "price": price,
                                "product_url": item.get("product_url", ""),
                                "in_stock": True,
                            },
                        )

            new_count += 1
            self.stdout.write(f"  + {brand} — {name}")

        return new_count, skip_count

    def _map_concerns_to_ingredients(self):
        for concern_key, inci_names in CONCERN_INGREDIENT_MAP.items():
            try:
                concern = SkinConcern.objects.get(internal_key=concern_key)
            except SkinConcern.DoesNotExist:
                continue

            for name in inci_names:
                try:
                    ing = Ingredient.objects.get(inci_name__iexact=name)
                    ing.concerns_supported.add(concern)
                except Ingredient.DoesNotExist:
                    pass

    def _auto_tag_all(self):
        products = Product.objects.prefetch_related(
            "product_ingredients__ingredient__concerns_supported",
        ).all()
        count = 0
        for p in products:
            auto_tag_product(p)
            count += 1
        return count
