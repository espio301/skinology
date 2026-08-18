"""
Management command to update PubMed evidence scores for all ingredient–concern pairs.

Usage:
    python manage.py update_evidence                          # update all pairs
    python manage.py update_evidence --ingredient "Retinol"   # single ingredient
    python manage.py update_evidence --concern "anti-aging"   # single concern
    python manage.py update_evidence --dry-run                # show queries only
"""
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from api.models import Ingredient, SkinConcern, IngredientConcernEvidence
from api.services.pubmed_client import (
    build_query, get_pubmed_count, get_pubmed_ids,
    get_article_summaries, classify_tier, throttle,
)


class Command(BaseCommand):
    help = 'Query PubMed and update evidence tiers for ingredient–concern pairs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingredient',
            type=str,
            default=None,
            help='Filter to a single ingredient by INCI or common name',
        )
        parser.add_argument(
            '--concern',
            type=str,
            default=None,
            help='Filter to a single concern by internal_key',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print queries without hitting PubMed API',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find ingredients with pubmed_terms populated
        ingredients = Ingredient.objects.exclude(pubmed_terms=[])
        if options['ingredient']:
            ingredients = ingredients.filter(
                models.Q(inci_name__iexact=options['ingredient']) |
                models.Q(common_name__iexact=options['ingredient'])
            )

        # Find concerns with pubmed_terms populated
        concerns = SkinConcern.objects.exclude(pubmed_terms=[])
        if options['concern']:
            concerns = concerns.filter(internal_key=options['concern'])

        if not ingredients.exists():
            self.stdout.write(self.style.WARNING('No ingredients with pubmed_terms found.'))
            return
        if not concerns.exists():
            self.stdout.write(self.style.WARNING('No concerns with pubmed_terms found.'))
            return

        updated = 0
        start = timezone.now()

        for ingredient in ingredients:
            for concern in concerns:
                query = build_query(ingredient, concern)
                if not query:
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [DRY RUN] {ingredient} × {concern}:\n'
                        f'    {query}'
                    )
                    continue

                count = get_pubmed_count(query)
                tier = classify_tier(count)
                throttle()

                # Fetch top 5 article references for non-zero counts
                top_articles = []
                if count > 0:
                    pmids = get_pubmed_ids(query, max_results=5)
                    throttle()
                    if pmids:
                        top_articles = get_article_summaries(pmids)
                        throttle()

                evidence, created = IngredientConcernEvidence.objects.update_or_create(
                    ingredient=ingredient,
                    concern=concern,
                    defaults={
                        'pubmed_count': count,
                        'evidence_tier': tier,
                        'query_used': query,
                        'top_articles': top_articles,
                        'last_queried': timezone.now(),
                    },
                )

                articles_msg = f', {len(top_articles)} articles' if top_articles else ''
                status = '✓ created' if created else '✓ updated'
                self.stdout.write(
                    f'  {ingredient} × {concern}: '
                    f'{count:,} → {tier}{articles_msg} {status}'
                )

                updated += 1
                throttle()

        elapsed = (timezone.now() - start).total_seconds()
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nDry run complete.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nUpdated {updated} evidence scores in {elapsed:.1f}s'
            ))
