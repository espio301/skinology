import os
import sys

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Product, SkinConcern, IngredientConcernEvidence

p = Product.objects.filter(name__icontains="9wishes").first()
if not p:
    p = Product.objects.filter(name__icontains="Rice 72").first()

if p:
    print(f"Product ID: {p.id}")
    print(f"Brand: {p.brand}")
    print(f"Name: {p.name}")
    print("Raw INCI:", p.raw_inci)

    print("\nLinked ProductIngredients:")
    pi_map = {}
    for pi in p.product_ingredients.select_related('ingredient').order_by('order'):
        inci = pi.ingredient.inci_name
        pi_map[pi.ingredient_id] = (pi.order, inci, pi.concentration)
        print(f"  #{pi.order}: {inci} (ID: {pi.ingredient_id})")

    # Find concern for oiliness / pores / sebum
    concerns = SkinConcern.objects.filter(label__icontains="oil") | SkinConcern.objects.filter(internal_key__icontains="pore")
    print("\nMatching Concerns:")
    for c in concerns:
        print(f"  Concern ID {c.id}: '{c.label}' (key: '{c.internal_key}', parent: {c.parent})")

    ev_qs = IngredientConcernEvidence.objects.filter(
        ingredient_id__in=pi_map.keys(),
        pubmed_count__gt=0,
    ).select_related('concern', 'ingredient')

    print(f"\nEvidence rows for {p.name}:")
    for ev in ev_qs:
        order, inci, conc = pi_map[ev.ingredient_id]
        print(f"  - Ingredient: {inci} (Rank #{order}) x Concern: '{ev.concern.label}' (key: '{ev.concern.internal_key}') -> PubMed count: {ev.pubmed_count}, Tier: {ev.evidence_tier}")
else:
    print("9wishes product not found.")
