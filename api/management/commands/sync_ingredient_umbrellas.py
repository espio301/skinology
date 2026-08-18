"""
Management command to evaluate and sync Ingredient -> IngredientUmbrella relationships
for all ingredients currently in the database.

Usage:
    python manage.py sync_ingredient_umbrellas
"""

from django.core.management.base import BaseCommand
from api.models import Ingredient, IngredientUmbrella
from scraper.parsers.synonym_table import get_umbrella_names


class Command(BaseCommand):
    help = 'Sync IngredientUmbrella relationships for all ingredients in database.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Syncing IngredientUmbrella relationships...')

        ingredients = Ingredient.objects.all()
        updated_count = 0
        link_count = 0

        for ingredient in ingredients:
            umbrella_names = get_umbrella_names(ingredient.inci_name)
            if not umbrella_names:
                continue

            for name in umbrella_names:
                umbrella, _ = IngredientUmbrella.objects.get_or_create(name=name)
                if not ingredient.umbrellas.filter(id=umbrella.id).exists():
                    ingredient.umbrellas.add(umbrella)
                    link_count += 1

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully evaluated {ingredients.count()} ingredients. '
            f'Assigned umbrellas to {updated_count} ingredients ({link_count} new links created).'
        ))
