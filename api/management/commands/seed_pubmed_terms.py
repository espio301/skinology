"""
Management command to seed PubMed search terms for existing ingredients and concerns.

Populates the pubmed_terms JSONField on Ingredient and SkinConcern models,
as well as pubmed_excluders on SkinConcern, so the update_evidence command
can build valid PubMed queries.

Usage:
    python manage.py seed_pubmed_terms
"""
from django.core.management.base import BaseCommand
from django.db import models as db_models
from api.models import Ingredient, SkinConcern


# ── PubMed terms for known ingredients ──────────────────────────────────────
# Each key matches an INCI name or common name (case-insensitive lookup).
# These will be written to ingredient.pubmed_terms as a list of dicts.

INGREDIENT_TERMS = {
    # AHAs / BHAs
    'Glycolic Acid': [
        {'term': 'Glycolates', 'field': 'Mesh'},
        {'term': 'glycolic acid', 'field': 'ti'},
    ],
    'Salicylic Acid': [
        {'term': 'Salicylic Acid', 'field': 'Mesh'},
        {'term': 'salicylic acid', 'field': 'ti'},
        {'term': 'BHA', 'field': 'ti'},
    ],
    'Lactic Acid': [
        {'term': 'Lactic Acid', 'field': 'Mesh'},
        {'term': 'lactic acid', 'field': 'ti'},
    ],
    # Retinoids
    'Retinol': [
        {'term': 'Retinol', 'field': 'Mesh'},
        {'term': 'retinol', 'field': 'ti'},
        {'term': 'Vitamin A', 'field': 'Mesh'},
    ],
    'Tretinoin': [
        {'term': 'Tretinoin', 'field': 'Mesh'},
        {'term': 'tretinoin', 'field': 'ti'},
        {'term': 'retinoic acid', 'field': 'ti'},
    ],
    'Retinal': [
        {'term': 'Retinaldehyde', 'field': 'Mesh'},
        {'term': 'retinal', 'field': 'ti'},
        {'term': 'retinaldehyde', 'field': 'ti'},
    ],
    # Antioxidants
    'Ascorbic Acid': [
        {'term': 'Ascorbic Acid', 'field': 'Mesh'},
        {'term': 'vitamin C', 'field': 'ti'},
        {'term': 'ascorbic acid', 'field': 'ti'},
    ],
    'Tocopherol': [
        {'term': 'Tocopherols', 'field': 'Mesh'},
        {'term': 'vitamin E', 'field': 'ti'},
        {'term': 'tocopherol', 'field': 'ti'},
    ],
    'Niacinamide': [
        {'term': 'Niacinamide', 'field': 'Mesh'},
        {'term': 'niacinamide', 'field': 'ti'},
        {'term': 'nicotinamide', 'field': 'ti'},
    ],
    # Moisturizers / Barrier
    'Hyaluronic Acid': [
        {'term': 'Hyaluronic Acid', 'field': 'Mesh'},
        {'term': 'hyaluronic acid', 'field': 'tiab'},
    ],
    'Ceramide NP': [
        {'term': 'Ceramides', 'field': 'Mesh'},
        {'term': 'ceramide', 'field': 'tiab'},
    ],
    'Squalane': [
        {'term': 'Squalane', 'field': 'Mesh'},
        {'term': 'squalane', 'field': 'tiab'},
        {'term': 'Squalene', 'field': 'Mesh'},
        {'term': 'squalene', 'field': 'tiab'},
    ],
    'Panthenol': [
        {'term': 'Pantothenic Acid', 'field': 'Mesh'},
        {'term': 'panthenol', 'field': 'tiab'},
        {'term': 'dexpanthenol', 'field': 'tiab'},
        {'term': 'd-panthenol', 'field': 'tiab'},
        {'term': 'provitamin B5', 'field': 'tiab'},
        {'term': 'pantothenol', 'field': 'tiab'},
    ],
    'Glycerin': [
        {'term': 'Glycerol', 'field': 'Mesh'},
        {'term': 'glycerin', 'field': 'tiab'},
        {'term': 'glycerol', 'field': 'tiab'},
    ],
    'Allantoin': [
        {'term': 'Allantoin', 'field': 'Mesh'},
        {'term': 'allantoin', 'field': 'tiab'},
    ],
    # Brightening / Pigmentation
    'Arbutin': [
        {'term': 'Arbutin', 'field': 'Mesh'},
        {'term': 'arbutin', 'field': 'ti'},
    ],
    'Tranexamic Acid': [
        {'term': 'Tranexamic Acid', 'field': 'Mesh'},
        {'term': 'tranexamic acid', 'field': 'ti'},
    ],
    'Kojic Acid': [
        {'term': 'kojic acid', 'field': 'ti'},
    ],
    'Alpha-Arbutin': [
        {'term': 'Arbutin', 'field': 'Mesh'},
        {'term': 'alpha-arbutin', 'field': 'ti'},
    ],
    # Peptides / Growth Factors
    'Copper Peptide': [
        {'term': 'copper peptide', 'field': 'ti'},
        {'term': 'GHK-Cu', 'field': 'ti'},
    ],
    'EGF': [
        {'term': 'Epidermal Growth Factor', 'field': 'Mesh'},
        {'term': 'EGF', 'field': 'ti'},
    ],
    # Sunscreen actives
    'Zinc Oxide': [
        {'term': 'Zinc Oxide', 'field': 'Mesh'},
        {'term': 'zinc oxide', 'field': 'ti'},
    ],
    'Titanium Dioxide': [
        {'term': 'Titanium', 'field': 'Mesh'},
        {'term': 'titanium dioxide', 'field': 'ti'},
    ],
    # Caffeine (multi-use)
    'Caffeine': [
        {'term': 'Caffeine', 'field': 'Mesh'},
        {'term': 'caffeine', 'field': 'ti'},
    ],
    # Centella / Cica
    'Centella Asiatica Extract': [
        {'term': 'Centella', 'field': 'Mesh'},
        {'term': 'centella asiatica', 'field': 'ti'},
        {'term': 'madecassoside', 'field': 'ti'},
    ],
    # Azelaic Acid
    'Azelaic Acid': [
        {'term': 'Azelaic Acid', 'field': 'tiab'},
        {'term': 'azelaic acid', 'field': 'ti'},
    ],
    # Snail Mucin
    'Snail Secretion Filtrate': [
        {'term': 'snail mucin', 'field': 'ti'},
        {'term': 'snail secretion', 'field': 'ti'},
    ],
    # Benzoyl Peroxide
    'Benzoyl Peroxide': [
        {'term': 'Benzoyl Peroxide', 'field': 'Mesh'},
        {'term': 'benzoyl peroxide', 'field': 'ti'},
    ],
}


# ── PubMed terms and excluders for known concerns ──────────────────────────
# Each key matches a SkinConcern.internal_key.

CONCERN_TERMS = {
    'acne': {
        'terms': [
            {'term': 'Acne Vulgaris', 'field': 'Mesh'},
            {'term': 'acne', 'field': 'tiab'},
            {'term': 'comedone*', 'field': 'tiab'},
            {'term': 'sebum', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'pores': {
        'terms': [
            {'term': 'pore*', 'field': 'tiab'},
            {'term': 'comedone*', 'field': 'tiab'},
            {'term': 'Sebaceous Glands', 'field': 'Mesh'},
            {'term': 'sebum', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'dryness': {
        'terms': [
            {'term': 'Skin Diseases', 'field': 'Mesh'},
            {'term': 'dry skin', 'field': 'tiab'},
            {'term': 'xerosis', 'field': 'tiab'},
            {'term': 'skin hydration', 'field': 'tiab'},
            {'term': 'moisturiz*', 'field': 'tiab'},
            {'term': 'transepidermal water loss', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'pigmentation': {
        'terms': [
            {'term': 'Hyperpigmentation', 'field': 'Mesh'},
            {'term': 'hyperpigmentation', 'field': 'tiab'},
            {'term': 'melasma', 'field': 'tiab'},
            {'term': 'dark spot*', 'field': 'tiab'},
            {'term': 'skin lightening', 'field': 'tiab'},
            {'term': 'melanogenesis', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'redness': {
        'terms': [
            {'term': 'Rosacea', 'field': 'Mesh'},
            {'term': 'rosacea', 'field': 'tiab'},
            {'term': 'erythema', 'field': 'tiab'},
            {'term': 'skin irritation', 'field': 'tiab'},
            {'term': 'sensitive skin', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'anti-aging': {
        'terms': [
            {'term': 'Skin Aging', 'field': 'Mesh'},
            {'term': 'photoaging', 'field': 'tiab'},
            {'term': 'anti-aging', 'field': 'tiab'},
            {'term': 'wrinkle*', 'field': 'tiab'},
            {'term': 'elastici*', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'sun-protection': {
        'terms': [
            {'term': 'Sunscreening Agents', 'field': 'Mesh'},
            {'term': 'sunscreen', 'field': 'tiab'},
            {'term': 'UV protection', 'field': 'tiab'},
            {'term': 'photoprotect*', 'field': 'tiab'},
            {'term': 'SPF', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'alopecia', 'field': 'tiab'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'photosensitiv*', 'field': 'tiab'},
            {'term': 'phototoxic*', 'field': 'tiab'},
        ],
    },
    # ── New sub-concerns (hierarchical taxonomy) ────────────────────────
    'fine-lines': {
        'terms': [
            {'term': 'Skin Aging', 'field': 'Mesh'},
            {'term': 'wrinkle*', 'field': 'tiab'},
            {'term': 'fine lines', 'field': 'tiab'},
            {'term': 'rhytide*', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'skin-firmness': {
        'terms': [
            {'term': 'Skin Aging', 'field': 'Mesh'},
            {'term': 'skin elastici*', 'field': 'tiab'},
            {'term': 'elastici*', 'field': 'tiab'},
            {'term': 'skin firmness', 'field': 'tiab'},
            {'term': 'collagen synthesis', 'field': 'tiab'},
            {'term': 'skin laxity', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'photoaging': {
        'terms': [
            {'term': 'Skin Aging', 'field': 'Mesh'},
            {'term': 'photoaging', 'field': 'tiab'},
            {'term': 'photodamag*', 'field': 'tiab'},
            {'term': 'solar elastosis', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'excess-sebum': {
        'terms': [
            {'term': 'Sebaceous Glands', 'field': 'Mesh'},
            {'term': 'sebum', 'field': 'tiab'},
            {'term': 'oily skin', 'field': 'tiab'},
            {'term': 'sebum production', 'field': 'tiab'},
            {'term': 'sebum secretion', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'seborrheic dermatitis', 'field': 'tiab'},
            {'term': 'atopic dermatitis', 'field': 'tiab'},
            {'term': 'psoriasis', 'field': 'tiab'},
        ],
    },
    'barrier-repair': {
        'terms': [
            {'term': 'Skin Barrier', 'field': 'tiab'},
            {'term': 'stratum corneum', 'field': 'tiab'},
            {'term': 'barrier function', 'field': 'tiab'},
            {'term': 'barrier repair', 'field': 'tiab'},
            {'term': 'barrier recovery', 'field': 'tiab'},
            {'term': 'epidermal barrier', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'tewl': {
        'terms': [
            {'term': 'transepidermal water loss', 'field': 'tiab'},
            {'term': 'trans-epidermal water loss', 'field': 'tiab'},
            {'term': 'TEWL', 'field': 'tiab'},
            {'term': 'transepidermal waterloss', 'field': 'tiab'},
            {'term': 'epidermal water loss', 'field': 'tiab'},
            {'term': 'Water Loss, Insensible', 'field': 'Mesh'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'dark-spots': {
        'terms': [
            {'term': 'Hyperpigmentation', 'field': 'Mesh'},
            {'term': 'dark spot*', 'field': 'tiab'},
            {'term': 'solar lentigo', 'field': 'tiab'},
            {'term': 'age spot*', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'melasma': {
        'terms': [
            {'term': 'Melanosis', 'field': 'Mesh'},
            {'term': 'melasma', 'field': 'tiab'},
            {'term': 'chloasma', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'rosacea': {
        'terms': [
            {'term': 'Rosacea', 'field': 'Mesh'},
            {'term': 'rosacea', 'field': 'tiab'},
            {'term': 'erythematotelangiectati*', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'post-procedure': {
        'terms': [
            {'term': 'postoperative skin care', 'field': 'tiab'},
            {'term': 'post-procedure skin', 'field': 'tiab'},
            {'term': 'wound healing', 'field': 'tiab'},
            {'term': 'Wound Healing', 'field': 'Mesh'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'surgical wound', 'field': 'tiab'},
        ],
    },
    'uv-defense': {
        'terms': [
            {'term': 'Sunscreening Agents', 'field': 'Mesh'},
            {'term': 'UV protection', 'field': 'tiab'},
            {'term': 'ultraviolet radiation', 'field': 'tiab'},
            {'term': 'SPF', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'photosensitiv*', 'field': 'tiab'},
            {'term': 'phototoxic*', 'field': 'tiab'},
        ],
    },
    'photodamage-prevention': {
        'terms': [
            {'term': 'photoprotect*', 'field': 'tiab'},
            {'term': 'photodamag*', 'field': 'tiab'},
            {'term': 'sun damage', 'field': 'tiab'},
            {'term': 'UV damage', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'photosensitiv*', 'field': 'tiab'},
            {'term': 'phototoxic*', 'field': 'tiab'},
        ],
    },
    # ── Standalone top-level concerns (no children) ─────────────────────
    'oiliness': {
        'terms': [
            {'term': 'Sebaceous Glands', 'field': 'Mesh'},
            {'term': 'sebum', 'field': 'tiab'},
            {'term': 'oily skin', 'field': 'tiab'},
            {'term': 'sebum production', 'field': 'tiab'},
            {'term': 'sebum secretion', 'field': 'tiab'},
            {'term': 'sebum control', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
            {'term': 'seborrheic dermatitis', 'field': 'tiab'},
        ],
    },
    'dullness': {
        'terms': [
            {'term': 'skin radiance', 'field': 'tiab'},
            {'term': 'skin brightening', 'field': 'tiab'},
            {'term': 'dull skin', 'field': 'tiab'},
            {'term': 'skin luminosity', 'field': 'tiab'},
            {'term': 'skin glow', 'field': 'tiab'},
            {'term': 'uneven skin tone', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
    'texture': {
        'terms': [
            {'term': 'skin texture', 'field': 'tiab'},
            {'term': 'skin roughness', 'field': 'tiab'},
            {'term': 'skin smoothness', 'field': 'tiab'},
            {'term': 'Chemical Exfoliation', 'field': 'Mesh'},
            {'term': 'exfoliat*', 'field': 'tiab'},
            {'term': 'desquamation', 'field': 'tiab'},
        ],
        'excluders': [
            {'term': 'Alopecia', 'field': 'Mesh'},
            {'term': 'hair', 'field': 'tiab'},
        ],
    },
}


class Command(BaseCommand):
    help = 'Seed PubMed search terms for existing ingredients and concerns'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding PubMed terms...\n')

        # ── Ingredients ─────────────────────────────────────────────────
        seeded_ingredients = 0
        for name, terms in INGREDIENT_TERMS.items():
            try:
                ingredient = Ingredient.objects.get(
                    db_models.Q(inci_name__iexact=name) |
                    db_models.Q(common_name__iexact=name)
                )
            except Ingredient.DoesNotExist:
                self.stdout.write(f'  ⚠ Ingredient not found: {name} (skipping)')
                continue
            except Ingredient.MultipleObjectsReturned:
                ingredient = Ingredient.objects.filter(
                    db_models.Q(inci_name__iexact=name) |
                    db_models.Q(common_name__iexact=name)
                ).first()

            ingredient.pubmed_terms = terms
            ingredient.save(update_fields=['pubmed_terms'])
            seeded_ingredients += 1
            self.stdout.write(f'  ✓ {ingredient.inci_name}: {len(terms)} terms')

        # ── Concerns ────────────────────────────────────────────────────
        seeded_concerns = 0
        for key, data in CONCERN_TERMS.items():
            try:
                concern = SkinConcern.objects.get(internal_key=key)
            except SkinConcern.DoesNotExist:
                # Try to create it if it doesn't exist
                self.stdout.write(f'  ⚠ Concern not found: {key} (skipping)')
                continue

            concern.pubmed_terms = data['terms']
            concern.pubmed_excluders = data.get('excluders', [])
            concern.save(update_fields=['pubmed_terms', 'pubmed_excluders'])
            seeded_concerns += 1
            self.stdout.write(
                f'  ✓ {concern.label}: {len(data["terms"])} terms, '
                f'{len(data.get("excluders", []))} excluders'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {seeded_ingredients} ingredients, {seeded_concerns} concerns.'
        ))
