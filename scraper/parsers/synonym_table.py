"""
Curated synonym → canonical INCI name mapping and umbrella groupings.

The SYNONYM_MAP is seeded with common alternate names found across retailer
sites.  Expand it over time as new products surface unrecognized names.

The UMBRELLA_MAP groups canonical INCI names under broad categories so users
can filter by "all Retinoids" or "all AHAs" without knowing every variant.
"""

import re

# ---------------------------------------------------------------------------
# Synonym → Canonical INCI name
# Keys are lowercase; values are the canonical mixed-case INCI name stored
# in the Ingredient model.
# ---------------------------------------------------------------------------

SYNONYM_MAP: dict[str, str] = {
    # Retinoids
    "retinal": "Retinaldehyde",
    "retinaldehyde": "Retinaldehyde",
    "retinol": "Retinol",
    "retinyl palmitate": "Retinyl Palmitate",
    "retinoic acid": "Tretinoin",
    "tretinoin": "Tretinoin",
    "adapalene": "Adapalene",
    "hydroxypinacolone retinoate": "Hydroxypinacolone Retinoate",
    "granactive retinoid": "Hydroxypinacolone Retinoate",

    # Glycols & Diols
    "1,2-hexanediol": "1,2-Hexanediol",
    "1, 2-hexanediol": "1,2-Hexanediol",
    "1 2-hexanediol": "1,2-Hexanediol",
    "1,2 hexanediol": "1,2-Hexanediol",
    "1.2-hexanediol": "1,2-Hexanediol",
    "1,2-octanediol": "1,2-Octanediol",
    "1,2-pentanediol": "1,2-Pentanediol",

    # Vitamin C forms
    "vitamin c": "Ascorbic Acid",
    "l-ascorbic acid": "Ascorbic Acid",
    "ascorbic acid": "Ascorbic Acid",
    "ascorbyl glucoside": "Ascorbyl Glucoside",
    "ascorbyl tetraisopalmitate": "Ascorbyl Tetraisopalmitate",
    "sodium ascorbyl phosphate": "Sodium Ascorbyl Phosphate",
    "magnesium ascorbyl phosphate": "Magnesium Ascorbyl Phosphate",
    "ethyl ascorbic acid": "3-O-Ethyl Ascorbic Acid",
    "3-o-ethyl ascorbic acid": "3-O-Ethyl Ascorbic Acid",

    # AHAs
    "glycolic acid": "Glycolic Acid",
    "lactic acid": "Lactic Acid",
    "mandelic acid": "Mandelic Acid",
    "tartaric acid": "Tartaric Acid",
    "citric acid": "Citric Acid",
    "malic acid": "Malic Acid",

    # BHAs
    "salicylic acid": "Salicylic Acid",
    "beta hydroxy acid": "Salicylic Acid",
    "bha": "Salicylic Acid",
    "betaine salicylate": "Betaine Salicylate",

    # PHAs
    "gluconolactone": "Gluconolactone",
    "lactobionic acid": "Lactobionic Acid",

    # Niacinamide / B vitamins
    "niacinamide": "Niacinamide",
    "vitamin b3": "Niacinamide",
    "nicotinamide": "Niacinamide",
    "panthenol": "Panthenol",
    "vitamin b5": "Panthenol",
    "d-panthenol": "Panthenol",
    "dexpanthenol": "Panthenol",

    # Hyaluronic acid
    "hyaluronic acid": "Hyaluronic Acid",
    "sodium hyaluronate": "Sodium Hyaluronate",
    "ha": "Hyaluronic Acid",

    # Peptides
    "matrixyl": "Palmitoyl Pentapeptide-4",
    "palmitoyl pentapeptide-4": "Palmitoyl Pentapeptide-4",
    "argireline": "Acetyl Hexapeptide-3",
    "acetyl hexapeptide-3": "Acetyl Hexapeptide-3",
    "copper peptide": "Copper Tripeptide-1",
    "copper tripeptide-1": "Copper Tripeptide-1",
    "ghk-cu": "Copper Tripeptide-1",

    # Ceramides
    "ceramide np": "Ceramide NP",
    "ceramide ap": "Ceramide AP",
    "ceramide eop": "Ceramide EOP",
    "ceramide ns": "Ceramide NS",
    "ceramide as": "Ceramide AS",
    "phytosphingosine": "Phytosphingosine",

    # Sunscreen actives
    "zinc oxide": "Zinc Oxide",
    "titanium dioxide": "Titanium Dioxide",
    "avobenzone": "Avobenzone",
    "octinoxate": "Ethylhexyl Methoxycinnamate",
    "ethylhexyl methoxycinnamate": "Ethylhexyl Methoxycinnamate",
    "homosalate": "Homosalate",
    "octocrylene": "Octocrylene",

    # Common moisturising / soothing
    "squalane": "Squalane",
    "squalene": "Squalene",
    "glycerin": "Glycerin",
    "glycerine": "Glycerin",
    "allantoin": "Allantoin",
    "centella asiatica": "Centella Asiatica Extract",
    "centella asiatica extract": "Centella Asiatica Extract",
    "madecassoside": "Madecassoside",
    "asiaticoside": "Asiaticoside",
    "shea butter": "Butyrospermum Parkii Butter",
    "butyrospermum parkii butter": "Butyrospermum Parkii Butter",
    "jojoba oil": "Simmondsia Chinensis Seed Oil",
    "simmondsia chinensis seed oil": "Simmondsia Chinensis Seed Oil",
    "tocopherol": "Tocopherol",
    "vitamin e": "Tocopherol",
    "alpha-tocopherol": "Tocopherol",

    # Brightening / anti-hyperpigmentation
    "arbutin": "Arbutin",
    "alpha arbutin": "Alpha-Arbutin",
    "alpha-arbutin": "Alpha-Arbutin",
    "kojic acid": "Kojic Acid",
    "tranexamic acid": "Tranexamic Acid",
    "azelaic acid": "Azelaic Acid",

    # Misc actives
    "benzoyl peroxide": "Benzoyl Peroxide",
    "sulfur": "Sulfur",
    "tea tree oil": "Melaleuca Alternifolia Leaf Oil",
    "melaleuca alternifolia leaf oil": "Melaleuca Alternifolia Leaf Oil",
    "bakuchiol": "Bakuchiol",
    "resveratrol": "Resveratrol",
    "ferulic acid": "Ferulic Acid",

    # Emollients / base ingredients
    "dimethicone": "Dimethicone",
    "cyclomethicone": "Cyclomethicone",
    "petrolatum": "Petrolatum",
    "mineral oil": "Mineral Oil",
    "paraffinum liquidum": "Mineral Oil",
    "aqua": "Water",
    "water": "Water",
    "eau": "Water",
}


# ---------------------------------------------------------------------------
# Umbrella → list of canonical INCI names
# ---------------------------------------------------------------------------

UMBRELLA_MAP: dict[str, list[str]] = {
    "Retinoids & Alternatives": [
        "Retinol",
        "Retinaldehyde",
        "Retinyl Palmitate",
        "Tretinoin",
        "Adapalene",
        "Hydroxypinacolone Retinoate",
        "Bakuchiol",  # plant-based retinol alternative
    ],
    "Vitamin C Derivatives": [
        "Ascorbic Acid",
        "Ascorbyl Glucoside",
        "Ascorbyl Tetraisopalmitate",
        "Sodium Ascorbyl Phosphate",
        "Magnesium Ascorbyl Phosphate",
        "3-O-Ethyl Ascorbic Acid",
    ],
    "AHAs": [
        "Glycolic Acid",
        "Lactic Acid",
        "Mandelic Acid",
        "Tartaric Acid",
        "Citric Acid",
        "Malic Acid",
    ],
    "BHAs": [
        "Salicylic Acid",
        "Betaine Salicylate",
    ],
    "PHAs": [
        "Gluconolactone",
        "Lactobionic Acid",
    ],
    "Niacinamide & B Vitamins": [
        "Niacinamide",
        "Panthenol",
    ],
    "Hyaluronic Acid": [
        "Hyaluronic Acid",
        "Sodium Hyaluronate",
    ],
    "Peptides": [
        "Palmitoyl Pentapeptide-4",
        "Acetyl Hexapeptide-3",
        "Copper Tripeptide-1",
    ],
    "Ceramides": [
        "Ceramide NP",
        "Ceramide AP",
        "Ceramide EOP",
        "Ceramide NS",
        "Ceramide AS",
        "Phytosphingosine",
    ],
    "Sunscreen Actives": [
        "Zinc Oxide",
        "Titanium Dioxide",
        "Avobenzone",
        "Ethylhexyl Methoxycinnamate",
        "Homosalate",
        "Octocrylene",
    ],
    "Antioxidants": [
        "Tocopherol",
        "Resveratrol",
        "Ferulic Acid",
        "Ascorbic Acid",
    ],
    "Centella / Cica": [
        "Centella Asiatica Extract",
        "Madecassoside",
        "Asiaticoside",
    ],
    "Brightening Agents": [
        "Arbutin",
        "Alpha-Arbutin",
        "Kojic Acid",
        "Tranexamic Acid",
        "Azelaic Acid",
        "Niacinamide",
    ],
    "Acne Fighters": [
        "Salicylic Acid",
        "Benzoyl Peroxide",
        "Sulfur",
        "Melaleuca Alternifolia Leaf Oil",
        "Azelaic Acid",
    ],
}

# Build a reverse lookup: canonical INCI → set of umbrella names
_REVERSE_UMBRELLA: dict[str, set[str]] = {}
for _umbrella, _members in UMBRELLA_MAP.items():
    for _member in _members:
        _REVERSE_UMBRELLA.setdefault(_member, set()).add(_umbrella)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(raw: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    return _WHITESPACE_RE.sub(" ", raw.strip()).lower()


def resolve_synonym(raw: str) -> str:
    """
    Resolve a raw ingredient string to its canonical INCI name.

    Returns the canonical name from SYNONYM_MAP if found, otherwise returns
    the input with title-casing applied (best-guess for new ingredients).
    """
    key = _normalize(raw)
    if key in SYNONYM_MAP:
        return SYNONYM_MAP[key]
    # Not in the table — return title-cased best guess
    return raw.strip().title()


def get_umbrella_names(inci_name: str) -> list[str]:
    """Return the umbrella category names for an INCI ingredient (via lookup and pattern matching)."""
    results = set(_REVERSE_UMBRELLA.get(inci_name, []))
    lower = inci_name.lower()

    # AHAs
    if any(k in lower for k in ['glycolic', 'lactic', 'mandelic', 'tartaric', 'citric', 'malic']):
        if 'polylactic' not in lower:
            results.add('AHAs')

    # BHAs
    if 'salicylic' in lower or 'betaine salicylate' in lower:
        results.add('BHAs')
        results.add('Acne Fighters')

    # PHAs
    if any(k in lower for k in ['gluconolactone', 'lactobionic', 'maltobionic', 'pha']):
        results.add('PHAs')

    # Hyaluronic Acid
    if 'hyaluron' in lower:
        results.add('Hyaluronic Acid')

    # Peptides
    if any(k in lower for k in ['peptide', 'polypeptide', 'matrixyl', 'argireline']):
        results.add('Peptides')

    # Vitamin C
    if 'ascorb' in lower:
        results.add('Vitamin C Derivatives')
        results.add('Antioxidants')

    # Retinoids
    if any(k in lower for k in ['retinol', 'retinal', 'retinoid', 'tretinoin', 'adapalene', 'bakuchiol', 'retinoate', 'retinyl']):
        results.add('Retinoids & Alternatives')

    # Ceramides
    if any(k in lower for k in ['ceramide', 'phytosphingosine', 'sphingosine']):
        results.add('Ceramides')

    # Niacinamide / B
    if any(k in lower for k in ['niacinamide', 'panthenol', 'vitamin b3', 'vitamin b5', 'nicotinamide', 'dexpanthenol']):
        results.add('Niacinamide & B Vitamins')

    # Centella / Cica
    if any(k in lower for k in ['centella', 'madecassoside', 'asiaticoside', 'cica']):
        results.add('Centella / Cica')

    # Brightening Agents
    if any(k in lower for k in ['arbutin', 'kojic', 'tranexamic', 'azelaic', 'niacinamide', 'glutathione', 'licorice', 'glycyrrhiza']):
        results.add('Brightening Agents')

    # Acne Fighters
    if any(k in lower for k in ['salicylic', 'benzoyl peroxide', 'sulfur', 'tea tree', 'melaleuca', 'azelaic']):
        results.add('Acne Fighters')

    # Sunscreen Actives
    if any(k in lower for k in ['zinc oxide', 'titanium dioxide', 'avobenzone', 'homosalate', 'octocrylene', 'octisalate', 'ethylhexyl methoxycinnamate', 'tinosorb', 'mexoryl', 'sunscreen', 'spf']):
        results.add('Sunscreen Actives')

    # Antioxidants
    if any(k in lower for k in ['tocopherol', 'resveratrol', 'ferulic', 'ascorb', 'green tea', 'camellia sinensis', 'glutathione', 'coenzyme q10', 'ubiquinone', 'astaxanthin']):
        results.add('Antioxidants')

    return sorted(results)

