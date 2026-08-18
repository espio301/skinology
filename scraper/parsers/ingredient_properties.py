"""
Curated reference tables for estimating product pH and strength from INCI lists.

Provides:
- INGREDIENT_PH_MAP: canonical INCI → (min_pH, max_pH) for pH-active ingredients
- INGREDIENT_POTENCY_MAP: canonical INCI → potency score + concentration overrides
- PRODUCT_TYPE_PH_DEFAULTS: product_type → (min_pH, max_pH) fallback ranges
- estimate_ph(product): returns (estimated_ph, confidence) tuple
- estimate_strength(product): returns strength tier string
"""

from __future__ import annotations
import re
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# pH ranges for pH-determining active ingredients
# When an ingredient appears high in the INCI list, the product's pH is
# likely formulated within this range for efficacy.
# ---------------------------------------------------------------------------

INGREDIENT_PH_MAP: dict[str, tuple[float, float]] = {
    # AHAs — require low pH for free-acid efficacy
    'Glycolic Acid':        (2.5, 4.0),
    'Lactic Acid':          (3.5, 4.5),
    'Mandelic Acid':        (3.0, 4.0),
    'Tartaric Acid':        (2.5, 3.5),
    'Citric Acid':          (3.0, 4.5),
    'Malic Acid':           (3.0, 4.0),

    # BHAs
    'Salicylic Acid':       (3.0, 4.0),
    'Betaine Salicylate':   (3.5, 4.5),

    # Vitamin C (L-Ascorbic Acid)
    'Ascorbic Acid':        (2.5, 3.5),

    # Other acids
    'Azelaic Acid':         (4.0, 5.0),
    'Kojic Acid':           (4.0, 5.0),
    'Tranexamic Acid':      (4.5, 6.0),
    'Ferulic Acid':         (3.0, 4.0),

    # Retinoids — slightly acidic formulation preferred
    'Retinol':              (4.0, 6.0),
    'Retinaldehyde':        (4.0, 5.5),
    'Hydroxypinacolone Retinoate': (4.5, 6.0),
    'Retinyl Palmitate':    (5.0, 6.5),

    # Niacinamide — mildly acidic to neutral
    'Niacinamide':          (5.0, 7.0),

    # Benzoyl Peroxide
    'Benzoyl Peroxide':     (4.0, 6.0),

    # Vitamin C derivatives (more pH-flexible than L-AA)
    'Ascorbyl Glucoside':           (5.0, 7.0),
    'Sodium Ascorbyl Phosphate':    (6.0, 7.5),
    'Magnesium Ascorbyl Phosphate': (6.0, 7.5),
    '3-O-Ethyl Ascorbic Acid':     (4.0, 6.0),
    'Ascorbyl Tetraisopalmitate':   (4.5, 6.5),

    # PHAs — gentler, higher pH
    'Gluconolactone':       (3.5, 5.0),
    'Lactobionic Acid':     (3.5, 5.0),
}


# ---------------------------------------------------------------------------
# Intrinsic potency scores (0–10) for known actives
# conc_boost maps concentration thresholds (%) to boosted scores
# ---------------------------------------------------------------------------

INGREDIENT_POTENCY_MAP: dict[str, dict] = {
    # ── Clinical-grade actives (8–10) ──
    'Tretinoin':                    {'base': 10},
    'Adapalene':                    {'base': 9},

    # ── High potency (7–8) ──
    'Glycolic Acid':                {'base': 7, 'conc_boost': {10: 8, 20: 9, 30: 10}},
    'Ascorbic Acid':                {'base': 7, 'conc_boost': {10: 8, 15: 9, 20: 10}},
    'Retinol':                      {'base': 7, 'conc_boost': {0.3: 7, 0.5: 8, 1.0: 9}},
    'Retinaldehyde':                {'base': 8},
    'Hydroxypinacolone Retinoate':  {'base': 7},
    'Benzoyl Peroxide':             {'base': 7, 'conc_boost': {2.5: 7, 5: 8, 10: 9}},
    'Salicylic Acid':               {'base': 6, 'conc_boost': {2: 7, 4: 8}},

    # ── Medium potency (4–6) ──
    'Azelaic Acid':                 {'base': 5, 'conc_boost': {10: 6, 15: 7, 20: 8}},
    'Lactic Acid':                  {'base': 5, 'conc_boost': {5: 5, 10: 6, 15: 7}},
    'Mandelic Acid':                {'base': 5, 'conc_boost': {5: 5, 10: 6}},
    'Kojic Acid':                   {'base': 5},
    'Zinc PCA':                     {'base': 6},
    'Kaolin':                       {'base': 5},
    'Bentonite':                    {'base': 5},
    'Camellia Sinensis Leaf Extract': {'base': 5},
    'Camellia Sinensis Leaf Water': {'base': 4},
    'Niacinamide':                  {'base': 3, 'conc_boost': {5: 4, 10: 5, 15: 6}},
    'Tranexamic Acid':              {'base': 4, 'conc_boost': {3: 5, 5: 6}},
    'Copper Tripeptide-1':          {'base': 5},
    'Bakuchiol':                    {'base': 4},
    'Caffeine':                     {'base': 3},
    'Ferulic Acid':                 {'base': 4},
    'Resveratrol':                  {'base': 4},
    'Sulfur':                       {'base': 6},
    'Alpha-Arbutin':                {'base': 3},
    'Arbutin':                      {'base': 3},
    'Betaine Salicylate':           {'base': 5},
    'Gluconolactone':               {'base': 4},
    'Lactobionic Acid':             {'base': 4},
    '3-O-Ethyl Ascorbic Acid':      {'base': 4},
    'Ascorbyl Glucoside':           {'base': 3},
    'Sodium Ascorbyl Phosphate':    {'base': 3},
    'Magnesium Ascorbyl Phosphate': {'base': 3},
    'Ascorbyl Tetraisopalmitate':   {'base': 3},
    'Retinyl Palmitate':            {'base': 4},

    # ── Low potency / soothing (1–3) ──
    'Rice Extract':                 {'base': 2},
    'Oryza Sativa (Rice) Bran Water': {'base': 2},
    'Panthenol':                    {'base': 2},
    'Allantoin':                    {'base': 2},
    'Centella Asiatica Extract':    {'base': 2},
    'Madecassoside':                {'base': 2},
    'Asiaticoside':                 {'base': 2},
    'Hyaluronic Acid':              {'base': 1},
    'Sodium Hyaluronate':           {'base': 1},
    'Glycerin':                     {'base': 1},
    'Squalane':                     {'base': 1},
    'Squalene':                     {'base': 1},
    'Ceramide NP':                  {'base': 1},
    'Ceramide AP':                  {'base': 1},
    'Ceramide EOP':                 {'base': 1},
    'Ceramide NS':                  {'base': 1},
    'Ceramide AS':                  {'base': 1},
    'Phytosphingosine':             {'base': 1},
    'Tocopherol':                   {'base': 2},
    'Zinc Oxide':                   {'base': 4},
    'Titanium Dioxide':             {'base': 2},
    'Melaleuca Alternifolia Leaf Oil': {'base': 3},
}


# ---------------------------------------------------------------------------
# Product type → fallback pH range (used when no pH-active is found in INCI)
# ---------------------------------------------------------------------------

PRODUCT_TYPE_PH_DEFAULTS: dict[str, tuple[float, float]] = {
    'cleanser':     (5.0, 6.5),
    'toner':        (5.0, 6.0),
    'serum':        (5.0, 6.5),
    'moisturizer':  (5.5, 6.5),
    'sunscreen':    (6.0, 7.5),
    'exfoliant':    (3.0, 4.5),
    'mask':         (5.0, 7.0),
    'eye_cream':    (6.0, 7.0),
    'oil':          (5.5, 7.0),
    'treatment':    (4.0, 6.0),
    'other':        (5.0, 7.0),
}


# ---------------------------------------------------------------------------
# Strength tier thresholds (5-tier finer-grained scale)
# ---------------------------------------------------------------------------

STRENGTH_TIERS = [
    ('ultra_gentle', 'Ultra-Gentle', 0, 1),    # score 0–1
    ('gentle',       'Gentle',       2, 3),     # score 2–3
    ('moderate',     'Moderate',     4, 5),     # score 4–5
    ('potent',       'Potent',       6, 7),     # score 6–7
    ('clinical',     'Clinical',     8, 10),    # score 8–10
]


# ---------------------------------------------------------------------------
# Confidence levels for pH estimation
# ---------------------------------------------------------------------------

PH_CONFIDENCE_HIGH = 'high'        # known acid/active with declared concentration
PH_CONFIDENCE_MEDIUM = 'medium'    # known pH-active found in top INCI positions
PH_CONFIDENCE_LOW = 'low'          # product-type fallback only


# ---------------------------------------------------------------------------
# Helper: parse concentration from ProductIngredient.concentration string
# ---------------------------------------------------------------------------

_CONC_RE = re.compile(r'([\d.]+)\s*%')


def _parse_concentration(conc_str: str) -> Optional[float]:
    """Extract numeric percentage from a concentration string like '2%' or '10 %'."""
    if not conc_str:
        return None
    m = _CONC_RE.search(conc_str)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_ph(product) -> Tuple[Optional[float], str]:
    """
    Estimate pH for a product using its INCI list.

    Returns (estimated_ph, confidence) where confidence is 'high', 'medium', or 'low'.

    Algorithm:
    1. Walk product_ingredients in INCI order (ascending = highest concentration first)
    2. Find the highest-ranked ingredient with a known pH range in INGREDIENT_PH_MAP
    3. If the active has a declared concentration %, bias toward lower end of range
       for acids (higher concentration → lower pH)
    4. If no pH-active is found, use PRODUCT_TYPE_PH_DEFAULTS
    5. Return the midpoint of the determined range, rounded to 1 decimal
    """
    product_ingredients = product.product_ingredients.select_related('ingredient').order_by('order')

    best_ph_active = None
    best_order = 999
    best_conc = None

    for pi in product_ingredients:
        inci = pi.ingredient.inci_name
        if inci in INGREDIENT_PH_MAP and pi.order < best_order:
            best_ph_active = inci
            best_order = pi.order
            best_conc = _parse_concentration(pi.concentration)

    if best_ph_active:
        ph_min, ph_max = INGREDIENT_PH_MAP[best_ph_active]

        if best_conc is not None:
            # Higher concentration → bias toward lower end of range for acids
            # Use a simple linear interpolation: higher conc = more acidic
            # Clamp between 0 and 1
            conc_factor = min(best_conc / 30.0, 1.0)  # normalize to 30% max
            estimated = ph_max - (ph_max - ph_min) * conc_factor
            return round(estimated, 1), PH_CONFIDENCE_HIGH

        # No concentration declared; use position-based bias
        # Active in top 5 = more likely at effective concentration
        if best_order <= 5:
            # Bias slightly toward lower end
            estimated = ph_min + (ph_max - ph_min) * 0.35
            return round(estimated, 1), PH_CONFIDENCE_MEDIUM
        else:
            # Active present but lower in list — probably trace amount
            estimated = ph_min + (ph_max - ph_min) * 0.65
            return round(estimated, 1), PH_CONFIDENCE_MEDIUM

    # No pH-active found — use product type fallback
    pt = product.product_type or 'other'
    ph_min, ph_max = PRODUCT_TYPE_PH_DEFAULTS.get(pt, (5.0, 7.0))
    estimated = (ph_min + ph_max) / 2.0
    return round(estimated, 1), PH_CONFIDENCE_LOW


def _get_potency_score(inci_name: str, order: int, concentration_str: str) -> int:
    """
    Get the effective potency score for a single ingredient.

    Uses concentration overrides if available, or order-based boost.
    """
    entry = INGREDIENT_POTENCY_MAP.get(inci_name)
    if not entry:
        return 0

    base = entry['base']
    conc = _parse_concentration(concentration_str)

    # Check concentration-based boost
    if conc is not None and 'conc_boost' in entry:
        # Find the highest threshold the concentration meets
        for threshold in sorted(entry['conc_boost'].keys(), reverse=True):
            if conc >= threshold:
                return entry['conc_boost'][threshold]

    # Order-based boost: active in top 5 gets +1 (capped at 10)
    if order <= 5:
        return min(base + 1, 10)

    return base


def estimate_strength(product) -> str:
    """
    Classify product strength on a 5-tier scale.

    Returns one of: 'ultra_gentle', 'gentle', 'moderate', 'potent', 'clinical'.

    Algorithm:
    1. For each product_ingredient, compute its effective potency score
    2. Take the MAX potency score across all ingredients
    3. Map to the 5-tier scale
    """
    product_ingredients = product.product_ingredients.select_related('ingredient').order_by('order')

    max_score = 0
    for pi in product_ingredients:
        score = _get_potency_score(
            pi.ingredient.inci_name,
            pi.order,
            pi.concentration,
        )
        max_score = max(max_score, score)

    # Map score to tier
    for tier_key, _tier_label, tier_min, tier_max in STRENGTH_TIERS:
        if tier_min <= max_score <= tier_max:
            return tier_key

    return 'ultra_gentle'


def get_strength_label(tier_key: str) -> str:
    """Return the human-readable label for a strength tier key."""
    for key, label, _, _ in STRENGTH_TIERS:
        if key == tier_key:
            return label
    return tier_key.replace('_', ' ').title()


def get_ph_confidence_explanation(confidence: str) -> str:
    """Return a user-facing explanation of pH confidence level."""
    explanations = {
        PH_CONFIDENCE_HIGH: (
            'High confidence — a pH-sensitive active ingredient with a declared '
            'concentration was found. The pH is estimated from known formulation '
            'requirements for this active at this concentration.'
        ),
        PH_CONFIDENCE_MEDIUM: (
            'Medium confidence — a pH-sensitive active ingredient was identified '
            'in the formula, but no exact concentration was declared. The pH is '
            'estimated from the ingredient\'s known effective pH range and its '
            'position in the ingredient list.'
        ),
        PH_CONFIDENCE_LOW: (
            'Low confidence — no pH-sensitive active ingredient was identified. '
            'The pH is estimated based on typical ranges for this product type '
            '(e.g., cleansers tend toward pH 5.0–6.5, moisturizers toward 5.5–6.5).'
        ),
    }
    return explanations.get(confidence, 'Unknown confidence level.')


def get_strength_explanation(product) -> str:
    """
    Generate a concise human-readable explanation of why a product received its strength/potency rating.
    """
    product_ingredients = product.product_ingredients.select_related('ingredient').order_by('order')

    driver_inci = None
    driver_score = 0
    driver_order = 999
    driver_conc = None

    for pi in product_ingredients:
        score = _get_potency_score(
            pi.ingredient.inci_name,
            pi.order,
            pi.concentration,
        )
        if score > driver_score:
            driver_score = score
            driver_inci = pi.ingredient.inci_name
            driver_order = pi.order
            driver_conc = pi.concentration

    tier_label = get_strength_label(estimate_strength(product))

    if driver_score >= 4 and driver_inci:
        conc_str = f" ({driver_conc})" if driver_conc else f" (Rank #{driver_order} in INCI list)"
        return f"{tier_label} strength driven by {driver_inci}{conc_str}."
    elif driver_score >= 2 and driver_inci:
        return f"{tier_label} formula featuring {driver_inci} with no high-potency exfoliants or clinical retinoids."
    else:
        return f"Ultra-gentle formula formulated primarily with hydrating and skin-soothing ingredients."
