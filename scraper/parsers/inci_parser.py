"""
INCI list parser.

Handles the full flow from raw comma-separated INCI string → normalised
canonical names → Django Ingredient records with umbrella assignments.
"""

import logging
import re

from django.db import transaction

from .synonym_table import resolve_synonym, get_umbrella_names

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize_inci_name(raw: str) -> str:
    """
    Strip leading/trailing whitespace, invisible characters, collapse internal whitespace, and
    lowercase.  This is the key used for synonym lookups.
    """
    # Remove zero-width formatting characters commonly found on copy-pasted text
    cleaned = re.sub(r'[\u200b-\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\ufeff]', '', raw)
    return _WHITESPACE_RE.sub(" ", cleaned.strip()).lower()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def clean_raw_inci_string(text: str) -> str:
    """
    Cleans raw INCI string by stripping product title headers, volume metrics,
    boilerplate warnings, section labels, and normalizing delimiters (commas and semicolons).
    Ingredients following the last ']' marker are extracted.
    """
    if not text:
        return ""

    # 1. Extract text following the FIRST ']' marker if present
    if ']' in text:
        first_bracket = text.find(']')
        after_bracket = text[first_bracket + 1:].strip()
        if len(after_bracket) > 3:
            text = after_bracket

    # Fix space-broken cosmetic INCI terms & normalize diols into safe placeholder tokens
    broken_terms = [
        (r'\bHyal\s+uronic\b', 'Hyaluronic'),
        (r'\bLa\s+uryl\b', 'Lauryl'),
        (r'\bHy\s+drogenated\b', 'Hydrogenated'),
        (r'\bAz\s+adirachta\b', 'Azadirachta'),
        (r'\bCoc\s+cinia\b', 'Coccinia'),
        (r'\bEg\s+gplant\b', 'Eggplant'),
        (r'\bCaprylic\s+capric\b', 'Caprylic/Capric'),
        (r'\bCapryliccapric\b', 'Caprylic/Capric'),
        (r'\b1\s*[\,\;s]*2\s*[\-\s]*[HL]exan(?:e\s*)?di-?ol\b', '1__hexanediol__'),
        (r'\b1\s*[\,\;s]*24\s*[\-\s]*[HL]exan(?:e\s*)?di-?ol\b', '1__hexanediol__'),
        (r'\b1\s*[\,\;s]*2\s*[\-\s]*[OO]ctan(?:e\s*)?di-?ol\b', '1__octanediol__'),
        (r'\b1\s*[\,\;s]*2\s*[\-\s]*[PP]entan(?:e\s*)?di-?ol\b', '1__pentanediol__'),
    ]
    for pattern, replacement in broken_terms:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Protect chemical numbers with internal commas or semicolons e.g. 1,2-Hexanediol or 1;2-Hexanediol
    text = re.sub(r'(\d+)\s*[,;]\s*(\d+)', r'\1__COMMA__\2', text)

    # Normalize semicolons into commas
    if ';' in text:
        text = text.replace(';', ',')

    # Auto-insert commas for space-separated INCI listings without commas or semicolons
    if ',' not in text and len(text) > 40:
        text = re.sub(r'([a-z0-9_\)])\s+([A-Z0-9])', r'\1, \2', text)

    # Section header patterns to replace with a comma separator across the string
    section_headers = [
        r'\bActive\s+Ingredients?\s*[:\n]?',
        r'\bInactive\s+Ingredients?\s*[:\n]?',
        r'\bKey\s+Ingredients?\s*[:\n]?',
        r'\bFull\s+Ingredients?\s*[:\n]?',
        r'\bFeatured\s+Ingredients?\s*[:\n]?',
        r'\bOther\s+Ingredients?\s*[:\n]?',
        r'\bEffective\s+Ingredients?\s*[:\n]?',
    ]
    for pattern in section_headers:
        text = re.sub(pattern, ', ', text, flags=re.IGNORECASE)

    # Remove boilerplate text e.g. "Ingredients Ingredient Lists May Change... Full Ingredients"
    text = re.sub(
        r'^(?:ingredients?\b[^\.\n:]*[\.:]|\bfull\s+ingredients?\b|\bingredient\s+list[s]?\b.*?\bfull\s+ingredients?\b|please\s+refer\s+to.*?(?:information|packaging)[\.\s]*|ingredient\s+lists?\s+may\s+change\b.*?(?:information|packaging)[\.\s]*)*',
        '',
        text,
        flags=re.IGNORECASE
    ).strip()

    # Remove leading bracket headers e.g. "[Product Name 50ml]" or "0.003 Fl. Oz. (0.1 G) X 4 Ea]"
    text = re.sub(r'^(?:\[[^\]]+\]|[^\]\n]*\])\s*', '', text).strip()

    # Remove set title headers e.g. "The Ordinary The Daily Set :"
    text = re.sub(r'^[^\:\n]+:\s*', '', text).strip()

    # Remove volume / weight standalone or parenthetical metrics e.g. "(1.69 fl. oz.(50ml))" or "5.07 fl. oz.(150ml)"
    text = re.sub(
        r'\(?\b\d+(?:\.\d+)?\s*(?:fl\.\s*oz|oz|ml|g|ct)\.?(?:\s*\(\d+(?:\.\d+)?\s*(?:g|ml|fl\.\s*oz)\))?\s*(?:x\s*\d+\s*(?:ea)?)?\]?\)?',
        '',
        text,
        flags=re.IGNORECASE
    ).strip()

    # Remove section markers like "(U Zone)", "(U Zone) Water"
    text = re.sub(r'^\([^\)]+\)\s*', '', text).strip()

    # Handle active ingredient inline lists e.g. "Avobenzone (2.70%) Homosalate (7.00%) Octisalate (4.50%) Water"
    text = re.sub(r'(\(\d+(?:\.\d+)?%\))\s+([A-Z][a-z]+)', r'\1, \2', text)

    return text


def parse_inci_list(raw_inci: str) -> list[str]:
    """
    Split a comma-separated INCI string into a list of canonical INCI names.
    Automatically cleans leading product titles, volume metrics, and boilerplate.

    Args:
        raw_inci: Full ingredient list as found on a product page, e.g.
                  "[Anua Toner 250ml] Water, Glycerin, Niacinamide..."

    Returns:
        Ordered list of canonical INCI names.
    """
    if not raw_inci or not raw_inci.strip():
        return []

    cleaned_raw = clean_raw_inci_string(raw_inci)
    parts = cleaned_raw.split(",")
    results: list[str] = []

    for part in parts:
        cleaned = part.replace('1__hexanediol__', '1,2-Hexanediol').replace('1__octanediol__', '1,2-Octanediol').replace('1__pentanediol__', '1,2-Pentanediol').replace('__COMMA__', ',').strip()
        if not cleaned:
            continue
        # Clean leftover brackets, colons, volume parentheticals
        cleaned = re.sub(r'^(?:\[[^\]]+\]|[^\]\n]*\])\s*', '', cleaned).strip()
        cleaned = re.sub(r'^\([^\)]+\)\s*', '', cleaned).strip()
        cleaned = re.sub(r'^[^\:\n]+:\s*', '', cleaned).strip()
        cleaned = re.sub(r'\(?\b\d+(?:\.\d+)?\s*(?:fl\.\s*oz|oz|ml|g|ct)\b.*?\)?', '', cleaned, flags=re.IGNORECASE).strip()
        # Clean inline concentration percentage/numeric parentheticals like "(0.1)" or "(0.025%)" or "(5%)"
        cleaned = re.sub(r'\(\s*\d+(?:\.\d+)?\s*%?\s*\)', '', cleaned).strip()
        if not cleaned:
            continue

        # Check for sub-product narrative names like "Hyaluronic Acid 2% + B5"
        # If it's a composite active title, try narrative extraction for known actives
        canonical = resolve_synonym(cleaned)
        
        # Don't add bogus long titles containing "Set" or volume noise as raw ingredients
        if len(cleaned.split()) > 6 and any(k in cleaned.lower() for k in ['set', 'oz', 'ml', 'fl.']):
            continue

        if canonical not in results:
            results.append(canonical)

    # Narrative fallback & set active extraction
    narrative_actives = [
        (r'\bsqualane\b', 'Squalane'),
        (r'\bhyaluronic\s+acid\b|\bha\b', 'Hyaluronic Acid'),
        (r'\bsodium\s+hyaluronate\b', 'Sodium Hyaluronate'),
        (r'\bniacinamide\b|\bb3\b', 'Niacinamide'),
        (r'\bpanthenol\b|\bb5\b', 'Panthenol'),
        (r'\bsalicylic\s+acid\b|\bbha\b', 'Salicylic Acid'),
        (r'\bglycolic\s+acid\b|\baha\b', 'Glycolic Acid'),
        (r'\blactic\s+acid\b', 'Lactic Acid'),
        (r'\bmandelic\s+acid\b', 'Mandelic Acid'),
        (r'\bceramides?\b', 'Ceramide NP'),
        (r'\bvitamin\s+c\b|\bascorbic\s+acid\b', 'Ascorbic Acid'),
        (r'\bretinal\b|\bretinaldehyde\b', 'Retinaldehyde'),
        (r'\bretinol\b', 'Retinol'),
        (r'\bbakuchiol\b', 'Bakuchiol'),
        (r'\bcentella\b|\bmadecassoside\b|\basiaticoside\b', 'Centella Asiatica Extract'),
        (r'\barbutin\b', 'Arbutin'),
        (r'\balpha-arbutin\b', 'Alpha-Arbutin'),
        (r'\bazelaic\s+acid\b', 'Azelaic Acid'),
        (r'\bgluconolactone\b', 'Gluconolactone'),
        (r'\bglycerin\b', 'Glycerin'),
        (r'\ballantoin\b', 'Allantoin'),
        (r'\badenosine\b', 'Adenosine'),
        (r'\btocopherol\b|\bvitamin\s+e\b', 'Tocopherol'),
        (r'\bzinc\s+oxide\b', 'Zinc Oxide'),
        (r'\bzinc\s+pca\b', 'Zinc PCA'),
        (r'\btitanium\s+dioxide\b', 'Titanium Dioxide'),
        (r'\bavobenzone\b', 'Avobenzone'),
        (r'\brice\b|\brice\s+bran\b', 'Rice Extract'),
        (r'\bpapaya\b', 'Papaya Fruit Extract'),
        (r'\bsea\s+buckthorn\b', 'Hippophae Rhamnoides Fruit Extract'),
        (r'\bcalendula\b', 'Calendula Officinalis Flower Extract'),
        (r'\baloe\b', 'Aloe Barbadensis Leaf Juice'),
        (r'\bbeta-glucan\b', 'Beta-Glucan'),
        (r'\bgreen\s+tea\b', 'Camellia Sinensis Leaf Water'),
    ]
    for pattern, canonical in narrative_actives:
        if re.search(pattern, raw_inci, re.IGNORECASE) and canonical not in results:
            results.append(canonical)

    return results


def extract_active_concentrations(text: str) -> dict[str, str]:
    """
    Extract active concentrations like '5% Niacinamide', 'Niacinamide (5%)', or 'Retinal(0.1)'.
    Returns mapping: canonical_inci_name -> concentration_str (e.g. {'Retinaldehyde': '0.1%'})
    """
    if not text:
        return {}

    conc_map = {}

    # Pattern 1: 'Retinal(0.1)' or 'Retinal (0.025%)' or 'Niacinamide(5)'
    matches_parenthetical = re.findall(r'([A-Za-z\-]+(?:\s+[A-Za-z\-]+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*%?\s*\)', text)
    for ing_text, conc in matches_parenthetical:
        canonical = resolve_synonym(ing_text)
        if canonical:
            conc_map[canonical] = f"{float(conc):g}%"

    # Pattern 2: '5% Niacinamide' or '0.1% Retinal'
    matches1 = re.findall(r'(\d+(?:\.\d+)?%)\s+([A-Za-z\-]+(?:\s+[A-Za-z\-]+)?)', text)
    for conc, ing_text in matches1:
        canonical = resolve_synonym(ing_text)
        if canonical:
            conc_map[canonical] = conc

    # Pattern 3: 'Niacinamide 5%' or 'Retinal 0.1%'
    matches2 = re.findall(r'([A-Za-z\-]+(?:\s+[A-Za-z\-]+)?)\s*\(?\s*(\d+(?:\.\d+)?%)\s*\)?', text)
    for ing_text, conc in matches2:
        canonical = resolve_synonym(ing_text)
        if canonical:
            conc_map[canonical] = conc

    return conc_map


# ---------------------------------------------------------------------------
# Django integration — match or create Ingredient records
# ---------------------------------------------------------------------------

def match_or_create_ingredients(inci_names: list[str]):
    """
    For each canonical INCI name, look up an existing ``Ingredient`` record
    (checking both ``inci_name`` exact match and the ``synonyms`` JSON list).
    If none is found, create a new ``Ingredient`` and auto-assign umbrella
    groups.

    Args:
        inci_names: List of canonical INCI names (output of ``parse_inci_list``).

    Returns:
        Ordered list of ``Ingredient`` instances matching the input order.
    """
    # Deferred import to avoid circular import at module load time.
    from api.models import Ingredient, IngredientUmbrella  # noqa: E402

    ingredients = []

    with transaction.atomic():
        for name in inci_names:
            ingredient = _find_ingredient(Ingredient, name)

            if ingredient is None:
                ingredient = Ingredient.objects.create(
                    inci_name=name,
                    common_name=name,
                    synonyms=[name.lower()],
                )
                logger.info("Created new Ingredient: %s", name)

                # Auto-assign umbrella groups
                umbrella_names = get_umbrella_names(name)
                for umb_name in umbrella_names:
                    umbrella, _ = IngredientUmbrella.objects.get_or_create(
                        name=umb_name,
                    )
                    ingredient.umbrellas.add(umbrella)

            ingredients.append(ingredient)

    return ingredients


def _find_ingredient(Ingredient, canonical_name: str):
    """
    Try to find an existing Ingredient by:
      1. Exact match on inci_name (case-insensitive).
      2. Checking the synonyms JSON list for a match.
    """
    # 1. Exact inci_name match
    try:
        return Ingredient.objects.get(inci_name__iexact=canonical_name)
    except Ingredient.DoesNotExist:
        pass

    # 2. Search through synonyms JSON lists
    # Since synonyms is a JSONField (list of strings), we check for containment.
    lowered = canonical_name.lower()
    for ing in Ingredient.objects.all():
        if isinstance(ing.synonyms, list) and lowered in [
            s.lower() for s in ing.synonyms
        ]:
            return ing

    return None
