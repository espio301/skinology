"""Debug sorting for a specific concern to see top-ranked products and their scores."""
from django.core.management.base import BaseCommand
from django.db import models as db_models
import re

from api.models import Product, SkinConcern, IngredientConcernEvidence, ProductIngredient
from api.filters import ProductFilter
from scraper.parsers.ingredient_properties import INGREDIENT_POTENCY_MAP


EVIDENCE_MULTIPLIER = {
    'well_founded': 3.0,
    'studied': 2.0,
    'prospective': 1.0,
}

STRENGTH_RANK = {
    'clinical': 5,
    'potent': 4,
    'moderate': 3,
    'gentle': 2,
    'ultra_gentle': 1,
}


def position_bonus(order):
    if order <= 1:
        return 2.0
    if order <= 5:
        return 1.5 + (5 - order) * 0.125
    if order <= 20:
        return 1.0 + (20 - order) * (0.5 / 15)
    return 1.0


def parse_concentration(conc_str):
    if not conc_str:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*%', conc_str)
    return float(m.group(1)) if m else None


def get_potency_score(inci_name, concentration_pct=None):
    entry = INGREDIENT_POTENCY_MAP.get(inci_name)
    if not entry:
        return 1
    base = entry['base']
    if concentration_pct is not None and 'conc_boost' in entry:
        for threshold in sorted(entry['conc_boost'].keys(), reverse=True):
            if concentration_pct >= threshold:
                return entry['conc_boost'][threshold]
    return base


class Command(BaseCommand):
    help = 'Debug priority sorting for a specific concern'

    def add_arguments(self, parser):
        parser.add_argument('--concern', type=str, default='anti-aging',
                            help='Internal key or ID of concern')
        parser.add_argument('--top', type=int, default=15,
                            help='Number of top products to show')
        parser.add_argument('--product', type=str, default=None,
                            help='Name substring to debug a specific product')

    def handle(self, *args, **options):
        concern_key = options['concern']

        # Find concern
        if concern_key.isdigit():
            concern = SkinConcern.objects.get(id=int(concern_key))
        else:
            concern = SkinConcern.objects.filter(internal_key=concern_key).first()
            if not concern:
                concern = SkinConcern.objects.filter(label__icontains=concern_key).first()

        if not concern:
            self.stdout.write(self.style.ERROR(f'Concern not found: {concern_key}'))
            return

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"Concern: {concern.label} (ID={concern.id}, key={concern.internal_key})")
        children = list(concern.children.all())
        self.stdout.write(f"Sub-concerns: {[c.internal_key for c in children]}")

        # Get all concern IDs (parent + children)
        all_concern_ids = [concern.id] + [c.id for c in children]

        # Filter products
        filterset = ProductFilter({'concerns': str(concern.id)}, queryset=Product.objects.all())
        qs = filterset.qs
        self.stdout.write(f"Products matching: {qs.count()}")

        # Score each product
        scored = []
        priority_keys = [str(concern.id)]
        key_order = {str(concern.id): 0, concern.internal_key: 0}

        for product in qs.prefetch_related('product_ingredients__ingredient'):
            pi_list = list(product.product_ingredients.select_related('ingredient').all())
            if not pi_list:
                scored.append((product, 0, 0, 0, []))
                continue

            pi_map = {}
            for pi in pi_list:
                pi_map[pi.ingredient_id] = {
                    'order': pi.order,
                    'inci_name': pi.ingredient.inci_name,
                    'concentration': pi.concentration,
                }

            ev_qs = IngredientConcernEvidence.objects.filter(
                ingredient_id__in=pi_map.keys(),
                pubmed_count__gt=0,
            ).select_related('concern', 'concern__parent')

            best_scores = {}
            ingredient_details = []
            for ev in ev_qs:
                p_key = ev.concern.parent.internal_key if ev.concern.parent else ev.concern.internal_key
                c_key = ev.concern.internal_key
                p_id = str(ev.concern.parent.id) if ev.concern.parent else str(ev.concern.id)
                c_id = str(ev.concern.id)

                # Only care about our concern
                if str(ev.concern.id) not in [str(cid) for cid in all_concern_ids] and \
                   (ev.concern.parent_id and str(ev.concern.parent_id) not in [str(cid) for cid in all_concern_ids]):
                    continue

                ing_info = pi_map.get(ev.ingredient_id)
                if not ing_info:
                    continue

                conc_pct = parse_concentration(ing_info['concentration'])
                potency = get_potency_score(ing_info['inci_name'], conc_pct)
                pos_bonus = position_bonus(ing_info['order'])
                ev_weight = EVIDENCE_MULTIPLIER.get(ev.evidence_tier, 1.0)
                relevance = potency * pos_bonus * ev_weight

                ingredient_details.append({
                    'name': ing_info['inci_name'],
                    'order': ing_info['order'],
                    'conc': ing_info['concentration'],
                    'potency': potency,
                    'pos_bonus': round(pos_bonus, 2),
                    'ev_tier': ev.evidence_tier,
                    'ev_weight': ev_weight,
                    'concern': ev.concern.internal_key,
                    'pubmed_count': ev.pubmed_count,
                    'relevance': round(relevance, 1),
                })

                for key in (p_key, c_key, p_id, c_id):
                    best_scores[key] = max(best_scores.get(key, 0), relevance)

            rel_score = 0
            for key, idx in key_order.items():
                rel = best_scores.get(key, 0)
                rel_score += rel

            strength_score = STRENGTH_RANK.get(product.strength, 1)
            rating = float(product.review_rating or 0)

            scored.append((product, rel_score, strength_score, rating, ingredient_details))

        scored.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

        top_n = options['top']
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"TOP {top_n} PRODUCTS (sorted by relevance)")
        self.stdout.write(f"{'='*80}")

        for idx, (product, rel, strength, rating, details) in enumerate(scored[:top_n], 1):
            self.stdout.write(f"\n#{idx} [{product.id}] {product.brand} — {product.name}")
            self.stdout.write(f"   Relevance={rel:.1f} | Strength={product.strength} ({strength}) | Rating={rating}")
            # Show contributing ingredients sorted by relevance
            details.sort(key=lambda d: d['relevance'], reverse=True)
            for d in details[:5]:
                self.stdout.write(
                    f"     → #{d['order']} {d['name']}"
                    f" | potency={d['potency']} × pos={d['pos_bonus']} × ev={d['ev_weight']} ({d['ev_tier']}, {d['pubmed_count']} papers)"
                    f" = {d['relevance']}"
                    f"  [concern: {d['concern']}]"
                )

        # If a specific product was requested, show full detail
        if options['product']:
            search_term = options['product']
            for product, rel, strength, rating, details in scored:
                if search_term.lower() in product.name.lower():
                    self.stdout.write(f"\n{'='*80}")
                    self.stdout.write(f"DETAILED: {product.brand} — {product.name}")
                    self.stdout.write(f"Relevance={rel:.1f} | Strength={product.strength}")
                    details.sort(key=lambda d: d['relevance'], reverse=True)
                    for d in details:
                        self.stdout.write(
                            f"  #{d['order']} {d['name']}"
                            f" | potency={d['potency']} × pos={d['pos_bonus']} × ev={d['ev_weight']} ({d['ev_tier']}, {d['pubmed_count']})"
                            f" = {d['relevance']}"
                            f"  [{d['concern']}]"
                        )
                    break
