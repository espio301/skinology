"""
PubMed E-Utilities client for querying article counts.

Uses NCBI's esearch.fcgi with rettype=count to avoid fetching full results.
Only retrieves the count of matching articles for evidence tier classification.
"""
import time
import logging
import xml.etree.ElementTree as ET

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ESEARCH_URL = getattr(
    settings, 'NCBI_ESEARCH_URL',
    'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
)
API_KEY = getattr(settings, 'NCBI_API_KEY', '')
REQUEST_DELAY = getattr(settings, 'PUBMED_REQUEST_DELAY', 0.35)
THRESHOLDS = getattr(settings, 'PUBMED_EVIDENCE_THRESHOLDS', {
    'well_founded': 200,
    'studied': 50,
})


def _format_term_group(terms):
    """
    Convert a list of term dicts into a PubMed query fragment.

    Input:  [{"term": "Caffeine", "field": "Mesh"}, {"term": "caffeine", "field": "tiab"}]
    Output: ("Caffeine"[Mesh] OR caffeine[tiab])
    """
    if not terms:
        return ''
    parts = []
    for t in terms:
        term = t['term']
        field = t['field']
        # MeSH terms get quotes, tiab terms get quotes only if multi-word or contain special chars
        if field.lower() == 'mesh':
            parts.append(f'"{term}"[{field}]')
        else:
            # Use quotes for multi-word terms, bare for single words/wildcards
            if ' ' in term or '-' in term:
                parts.append(f'"{term}"[{field}]')
            else:
                parts.append(f'{term}[{field}]')
    return '(' + ' OR '.join(parts) + ')'


SKIN_CONTEXT_TERMS = [
    {'term': 'Skin', 'field': 'Mesh'},
    {'term': 'Skin Care', 'field': 'Mesh'},
    {'term': 'skin', 'field': 'tiab'},
    {'term': 'skincare', 'field': 'tiab'},
    {'term': 'topical', 'field': 'tiab'},
    {'term': 'cutaneous', 'field': 'tiab'},
    {'term': 'dermatol*', 'field': 'tiab'},
]

# Ingredient INCI names (lowercase) → set of concern internal_keys where the
# ingredient is known to CAUSE or WORSEN the problem, not treat it.
# build_query() returns '' for these pairs so they score 0 with no API call.
CONTRAINDICATED_PAIRS = {
    # Retinoids — photosensitizing, drying, barrier-disrupting, irritating
    'retinol':          {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'dryness', 'tewl', 'barrier-repair', 'redness', 'rosacea'},
    'tretinoin':        {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'dryness', 'tewl', 'barrier-repair', 'redness', 'rosacea'},
    'retinal':          {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'dryness', 'tewl', 'barrier-repair', 'redness', 'rosacea'},
    # AHAs — photosensitizing, barrier-disrupting, irritating
    'glycolic acid':    {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'barrier-repair', 'tewl', 'redness', 'rosacea'},
    'lactic acid':      {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'barrier-repair', 'tewl', 'redness', 'rosacea'},
    # BHA — photosensitizing, drying, barrier-disrupting
    'salicylic acid':   {'sun-protection', 'uv-defense', 'photodamage-prevention',
                         'dryness', 'barrier-repair', 'tewl', 'rosacea'},
    # Benzoyl Peroxide — drying, barrier-damaging, irritating, photosensitizing
    'benzoyl peroxide': {'dryness', 'tewl', 'barrier-repair', 'redness', 'rosacea',
                         'sun-protection', 'uv-defense', 'photodamage-prevention'},
    # Kojic Acid — irritating, photosensitizing
    'kojic acid':       {'redness', 'rosacea',
                         'sun-protection', 'uv-defense', 'photodamage-prevention'},
}


def _is_contraindicated(ingredient, concern):
    """Check if an ingredient–concern pair is in the blocklist."""
    inci = getattr(ingredient, 'inci_name', '')
    key = getattr(concern, 'internal_key', '')
    blocked = CONTRAINDICATED_PAIRS.get(inci.lower(), set())
    return key in blocked


def build_query(ingredient, concern):
    """
    Build a full PubMed search query from an Ingredient and SkinConcern.

    Returns a string like:
        ("Caffeine"[Mesh] OR caffeine[ti]) AND ("Skin Aging"[Mesh] OR photoaging[tiab])
        AND ("Skin"[Mesh] OR skin[ti] OR topical[tiab] OR ...)
        NOT ("Alopecia"[Mesh] OR hair[tiab])

    Returns '' for contraindicated pairs (ingredient worsens the concern).
    """
    if _is_contraindicated(ingredient, concern):
        return ''

    ingredient_part = _format_term_group(ingredient.pubmed_terms)
    concern_part = _format_term_group(concern.pubmed_terms)
    excluder_part = _format_term_group(concern.pubmed_excluders)
    skin_context_part = _format_term_group(SKIN_CONTEXT_TERMS)

    if not ingredient_part or not concern_part:
        return ''

    query = f'{ingredient_part} AND {concern_part} AND {skin_context_part}'
    if excluder_part:
        query += f' NOT {excluder_part}'

    return query


def get_pubmed_count(query):
    """
    Query PubMed esearch API and return the count of matching articles.

    Uses rettype=count to only get the count (no article data fetched).
    Returns 0 on any error.
    """
    if not query:
        return 0

    params = {
        'db': 'pubmed',
        'term': query,
        'rettype': 'count',
    }
    if API_KEY:
        params['api_key'] = API_KEY

    try:
        resp = requests.get(ESEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        count_el = root.find('Count')
        if count_el is not None and count_el.text:
            return int(count_el.text)
        logger.warning('No <Count> element in PubMed response for query: %s', query)
        return 0
    except requests.RequestException as e:
        logger.error('PubMed API request failed: %s', e)
        return 0
    except ET.ParseError as e:
        logger.error('Failed to parse PubMed XML response: %s', e)
        return 0


def get_pubmed_ids(query, max_results=5):
    """
    Query PubMed esearch and return a list of up to `max_results` PMIDs.

    Sorted by relevance (default PubMed sort).
    Returns an empty list on any error.
    """
    if not query:
        return []

    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'sort': 'relevance',
    }
    if API_KEY:
        params['api_key'] = API_KEY

    try:
        resp = requests.get(ESEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        id_list = root.find('IdList')
        if id_list is None:
            return []
        return [id_el.text for id_el in id_list.findall('Id') if id_el.text]
    except (requests.RequestException, ET.ParseError) as e:
        logger.error('PubMed esearch for IDs failed: %s', e)
        return []


ESUMMARY_URL = getattr(
    settings, 'NCBI_ESUMMARY_URL',
    'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
)


def get_article_summaries(pmids):
    """
    Fetch article metadata (title, publication date) from PubMed esummary.

    Args:
        pmids: list of PMID strings, e.g. ['12345', '67890']

    Returns:
        list of dicts: [{"pmid": "12345", "title": "...", "year": "2023"}, ...]
    """
    if not pmids:
        return []

    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'json',
    }
    if API_KEY:
        params['api_key'] = API_KEY

    try:
        resp = requests.get(ESUMMARY_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result_block = data.get('result', {})
        uid_list = result_block.get('uids', [])

        articles = []
        for uid in uid_list:
            doc = result_block.get(uid, {})
            title = doc.get('title', '').rstrip('.')
            pub_date = doc.get('pubdate', '')
            # Extract year from pubdate (e.g. "2023 Jan 15" → "2023")
            year = pub_date.split(' ')[0] if pub_date else ''
            articles.append({
                'pmid': str(uid),
                'title': title,
                'year': year,
            })
        return articles
    except (requests.RequestException, ValueError, KeyError) as e:
        logger.error('PubMed esummary failed: %s', e)
        return []


def classify_tier(count):
    """
    Classify a PubMed article count into an evidence tier.

    Returns one of: 'well_founded', 'studied', 'prospective'
    """
    if count >= THRESHOLDS['well_founded']:
        return 'well_founded'
    elif count >= THRESHOLDS['studied']:
        return 'studied'
    else:
        return 'prospective'


def throttle():
    """Sleep between API requests to respect NCBI rate limits."""
    time.sleep(REQUEST_DELAY)

