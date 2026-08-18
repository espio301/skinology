"""
Management command to map concerns to ingredients based on CONCERN_INGREDIENT_MAP
and auto-tag all products.

Usage:
    python manage.py sync_ingredient_concerns
"""

from django.core.management.base import BaseCommand
from api.models import Ingredient, SkinConcern
from scraper.data.seed_products import CONCERN_INGREDIENT_MAP
from scraper.taggers import auto_tag_all_products


class Command(BaseCommand):
    help = 'Sync SkinConcern relationships for all ingredients and auto-tag products.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Syncing concern mappings to ingredients...')

        mapped_count = 0
        link_count = 0

        for concern_key, ingredient_names in CONCERN_INGREDIENT_MAP.items():
            try:
                concern = SkinConcern.objects.get(internal_key=concern_key)
            except SkinConcern.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Concern not found: {concern_key}'))
                continue

            for name in ingredient_names:
                # Find the ingredient by inci_name or common_name case-insensitive
                ing = Ingredient.objects.filter(inci_name__iexact=name).first()
                if not ing:
                    ing = Ingredient.objects.filter(common_name__iexact=name).first()
                
                # Check through synonyms if still not found
                if not ing:
                    lowered = name.lower()
                    for candidate in Ingredient.objects.all():
                        if isinstance(candidate.synonyms, list) and lowered in [
                            s.lower() for s in candidate.synonyms
                        ]:
                            ing = candidate
                            break

                if ing:
                    if not ing.concerns_supported.filter(id=concern.id).exists():
                        ing.concerns_supported.add(concern)
                        link_count += 1
                    mapped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully linked {link_count} concern relationships to ingredients.'
        ))

        self.stdout.write('Auto-tagging all products...')
        tagged = auto_tag_all_products()
        self.stdout.write(self.style.SUCCESS(
            f'Successfully auto-tagged {tagged} products with concerns.'
        ))
