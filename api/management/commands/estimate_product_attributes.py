"""
Management command to estimate pH and strength for all products.

Uses the ingredient properties reference module to algorithmically compute
avg_ph, ph_confidence, and strength from each product's INCI list.

Usage:
    python manage.py estimate_product_attributes                  # all products
    python manage.py estimate_product_attributes --product "slug" # single product
    python manage.py estimate_product_attributes --dry-run        # preview only
"""
from django.core.management.base import BaseCommand

from api.models import Product
from scraper.parsers.ingredient_properties import (
    estimate_ph,
    estimate_strength,
    get_strength_label,
)


class Command(BaseCommand):
    help = 'Estimate pH and strength for products based on INCI ingredients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            default=None,
            help='Filter to a single product by slug',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print estimates without saving to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        products = Product.objects.prefetch_related(
            'product_ingredients__ingredient'
        )
        if options['product']:
            products = products.filter(slug=options['product'])

        if not products.exists():
            self.stdout.write(self.style.WARNING('No products found.'))
            return

        total = products.count()
        ph_updated = 0
        strength_updated = 0

        for i, product in enumerate(products, 1):
            # Estimate pH
            ph_val, ph_conf = estimate_ph(product)

            # Estimate strength
            strength_val = estimate_strength(product)
            strength_label = get_strength_label(strength_val)

            if dry_run:
                self.stdout.write(
                    f'  [{i}/{total}] {product.brand} — {product.name}\n'
                    f'    pH: {ph_val} (confidence: {ph_conf})\n'
                    f'    Strength: {strength_label} ({strength_val})'
                )
                continue

            changed = False
            if ph_val is not None:
                product.avg_ph = ph_val
                product.ph_confidence = ph_conf
                ph_updated += 1
                changed = True

            if strength_val:
                product.strength = strength_val
                strength_updated += 1
                changed = True

            if changed:
                product.save(update_fields=['avg_ph', 'ph_confidence', 'strength', 'updated_at'])

            if i % 50 == 0:
                self.stdout.write(f'  Processed {i}/{total} products...')

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n[DRY RUN] Would update {total} products.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone! Updated {total} products: '
                f'{ph_updated} pH estimates, {strength_updated} strength classifications.'
            ))
