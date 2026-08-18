import os
import sys

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Product, SkinConcern, IngredientConcernEvidence
from api.filters import ProductFilter

# Find the concern for Pore Care & Oil Control
pore_concern = SkinConcern.objects.filter(label__icontains="Pore").first()
print(f"Pore Concern: ID {pore_concern.id}, Label: '{pore_concern.label}', Key: '{pore_concern.internal_key}'")

# Let me filter products by this concern using ProductFilter
filterset = ProductFilter({'concerns': str(pore_concern.id)}, queryset=Product.objects.all())
qs = filterset.qs
print(f"Total products matching concern '{pore_concern.label}': {qs.count()}")

# Call ProductViewSet's apply_priority_sorting on this qs
from api.views import ProductViewSet
viewset = ProductViewSet()
sorted_qs = viewset.apply_priority_sorting(qs, [str(pore_concern.id)])

top_10 = list(sorted_qs[:10])
print("\nTop 10 products after priority sorting:")
for idx, p in enumerate(top_10, 1):
    print(f" #{idx} [ID {p.id}] {p.brand} — {p.name}")

# Inspect 9wishes specifically
p_9wishes = Product.objects.filter(name__icontains="9wishes").first()
if p_9wishes:
    print(f"\n9wishes Product ID: {p_9wishes.id}")
    print(f"9wishes Concerns: {[c.label for c in p_9wishes.concerns.all()]}")
    print("\n9wishes Evidence Rows:")
    pi_map = {pi.ingredient_id: (pi.order, pi.ingredient.inci_name) for pi in p_9wishes.product_ingredients.select_related('ingredient').all()}
    ev_qs = IngredientConcernEvidence.objects.filter(ingredient_id__in=pi_map.keys(), pubmed_count__gt=0).select_related('concern')
    for ev in ev_qs:
        order, inci = pi_map[ev.ingredient_id]
        print(f"   - #{order} {inci} x Concern '{ev.concern.label}' (ID {ev.concern.id}, key '{ev.concern.internal_key}') -> PubMed count {ev.pubmed_count}, Tier {ev.evidence_tier}")
