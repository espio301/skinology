from rest_framework import serializers
from collections import defaultdict
from api.models import (
    Ingredient, IngredientUmbrella, SkinConcern, Product, ProductIngredient,
    Retailer, RetailerListing, UserProfile, Routine, RoutineItem,
    ClickEvent, Article, IngredientConcernEvidence,
)


# ── Ingredient & Science ────────────────────────────────────────────────────

class IngredientUmbrellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientUmbrella
        fields = ['id', 'name', 'description']


class SkinConcernChildSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sub-concerns (no recursion)."""
    class Meta:
        model = SkinConcern
        fields = ['id', 'label', 'internal_key']


class SkinConcernSerializer(serializers.ModelSerializer):
    children = SkinConcernChildSerializer(many=True, read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent', read_only=True,
    )

    class Meta:
        model = SkinConcern
        fields = ['id', 'label', 'internal_key', 'description', 'parent_id', 'children']


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'url', 'source', 'summary', 'published_date']


def build_ingredient_concern_breakdown(ingredient):
    """
    Group an ingredient's evidence scores under parent concerns.
    Returns a list of parent concern objects, each containing sub-concerns
    with the ingredient's evidence tier, pubmed count, top articles, and query used.
    """
    evidence_qs = ingredient.evidence_scores.filter(
        pubmed_count__gt=0
    ).select_related('concern__parent')

    parent_map = defaultdict(lambda: {'_parent': None, 'sub_concerns': {}})

    for ev in evidence_qs:
        concern = ev.concern
        parent = concern.parent
        parent_obj = parent if parent else concern
        child_obj = concern if parent else concern

        parent_map[parent_obj.id]['_parent'] = {
            'id': parent_obj.id,
            'label': parent_obj.label,
            'internal_key': parent_obj.internal_key,
        }

        parent_map[parent_obj.id]['sub_concerns'][child_obj.id] = {
            'concern': {
                'id': child_obj.id,
                'label': child_obj.label,
                'internal_key': child_obj.internal_key,
            },
            'tier': ev.evidence_tier,
            'count': ev.pubmed_count,
            'articles': ev.top_articles or [],
            'query_used': ev.query_used,
        }

    res = []
    for pid, pdata in parent_map.items():
        sub_list = list(pdata['sub_concerns'].values())
        res.append({
            'parent': pdata['_parent'],
            'sub_concerns': sub_list,
        })
    return res


class IngredientConcernEvidenceSerializer(serializers.ModelSerializer):
    """Evidence score for a specific ingredient-concern pair."""
    concern = SkinConcernChildSerializer(read_only=True)

    class Meta:
        model = IngredientConcernEvidence
        fields = ['concern', 'evidence_tier', 'pubmed_count', 'last_queried', 'top_articles', 'query_used']


class IngredientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ingredient lists."""
    umbrellas = IngredientUmbrellaSerializer(many=True, read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)
    evidence_scores = IngredientConcernEvidenceSerializer(many=True, read_only=True)
    concern_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ['id', 'inci_name', 'common_name', 'description', 'umbrellas', 'articles', 'evidence_scores', 'concern_breakdown']

    def get_concern_breakdown(self, ingredient):
        return build_ingredient_concern_breakdown(ingredient)


class IngredientDetailSerializer(serializers.ModelSerializer):
    """Full serializer with science summary, linked articles, and evidence scores."""
    umbrellas = IngredientUmbrellaSerializer(many=True, read_only=True)
    concerns_supported = SkinConcernSerializer(many=True, read_only=True)
    articles = ArticleSerializer(many=True, read_only=True)
    evidence_scores = IngredientConcernEvidenceSerializer(many=True, read_only=True)
    concern_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = [
            'id', 'inci_name', 'common_name', 'description',
            'science_summary', 'synonyms', 'umbrellas',
            'concerns_supported', 'articles', 'evidence_scores', 'concern_breakdown',
        ]

    def get_concern_breakdown(self, ingredient):
        return build_ingredient_concern_breakdown(ingredient)

# ── Retailer ─────────────────────────────────────────────────────────────────

class RetailerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retailer
        fields = ['id', 'name', 'base_url']


class RetailerListingSerializer(serializers.ModelSerializer):
    retailer = RetailerSerializer(read_only=True)

    class Meta:
        model = RetailerListing
        fields = [
            'id', 'retailer', 'price', 'currency',
            'product_url', 'affiliate_url', 'in_stock', 'last_scraped',
        ]


# ── Product ──────────────────────────────────────────────────────────────────

class ProductIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientListSerializer(read_only=True)

    class Meta:
        model = ProductIngredient
        fields = ['id', 'ingredient', 'order', 'concentration']


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists / search results."""
    concerns = SkinConcernSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    strength_label = serializers.SerializerMethodField()
    strength_explanation = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'slug', 'image_url',
            'product_type', 'strength', 'strength_label', 'strength_explanation', 'concerns', 'min_price',
        ]

    def get_min_price(self, obj):
        listing = obj.retailer_listings.filter(in_stock=True).order_by('price').first()
        return str(listing.price) if listing and listing.price else None

    def get_strength_label(self, obj):
        from scraper.parsers.ingredient_properties import get_strength_label
        return get_strength_label(obj.strength) if obj.strength else None

    def get_strength_explanation(self, obj):
        from scraper.parsers.ingredient_properties import get_strength_explanation
        return get_strength_explanation(obj) if obj.strength else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer with ingredients, listings, concerns, and concern breakdown."""
    concerns = SkinConcernSerializer(many=True, read_only=True)
    product_ingredients = ProductIngredientSerializer(many=True, read_only=True)
    retailer_listings = RetailerListingSerializer(many=True, read_only=True)
    concern_breakdown = serializers.SerializerMethodField()
    strength_label = serializers.SerializerMethodField()
    strength_explanation = serializers.SerializerMethodField()
    ph_confidence_explanation = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'slug', 'description', 'image_url',
            'product_type', 'avg_ph', 'ph_confidence', 'ph_confidence_explanation',
            'strength', 'strength_label', 'strength_explanation',
            'raw_inci', 'concerns',
            'product_ingredients', 'retailer_listings', 'concern_breakdown',
            'created_at', 'updated_at',
        ]

    def get_strength_label(self, obj):
        from scraper.parsers.ingredient_properties import get_strength_label
        return get_strength_label(obj.strength) if obj.strength else None

    def get_strength_explanation(self, obj):
        from scraper.parsers.ingredient_properties import get_strength_explanation
        return get_strength_explanation(obj) if obj.strength else None

    def get_ph_confidence_explanation(self, obj):
        from scraper.parsers.ingredient_properties import get_ph_confidence_explanation
        return get_ph_confidence_explanation(obj.ph_confidence) if obj.ph_confidence else None

    def get_concern_breakdown(self, product):
        """
        Group the product's ingredients under parent concerns based on
        evidence scores. Returns a list of parent concern objects, each
        containing sub-concerns with their matched ingredient pills.

        Structure:
        [
          {
            "parent": {"id": 1, "label": "Anti-Aging"},
            "sub_concerns": [
              {
                "concern": {"id": 5, "label": "Fine Lines & Wrinkles"},
                "ingredients": [
                  {"id": 10, "inci_name": "Retinol", "tier": "well_founded", "count": 450}
                ]
              }
            ]
          }
        ]
        """
        # Collect all ingredient IDs for this product
        product_ingredient_ids = set(
            pi.ingredient_id for pi in product.product_ingredients.all()
        )
        if not product_ingredient_ids:
            return []

        # Build map of ingredient_id -> order & concentration for this product
        pi_map = {
            pi.ingredient_id: {
                'order': pi.order,
                'concentration': pi.concentration,
            }
            for pi in product.product_ingredients.all()
        }

        # Get all evidence scores for product ingredients with PubMed studies
        evidence_qs = IngredientConcernEvidence.objects.filter(
            ingredient_id__in=product_ingredient_ids,
            pubmed_count__gt=0,
        ).select_related('concern__parent', 'ingredient')

        # Build: parent_key -> { sub_concern_key -> [ingredient_scores] }
        parent_map = defaultdict(lambda: defaultdict(list))

        for ev in evidence_qs:
            concern = ev.concern
            parent = concern.parent

            parent_obj = parent if parent else concern
            child_obj = concern if parent else concern

            # De-duplicate: best tier per ingredient per sub-concern
            parent_map[parent_obj.id].setdefault('_parent', parent_obj)
            entry = {
                'ingredient_id': ev.ingredient_id,
                'inci_name': ev.ingredient.inci_name,
                'tier': ev.evidence_tier,
                'count': ev.pubmed_count,
                'articles': ev.top_articles or [],
                'query_used': ev.query_used,
                'order': pi_map.get(ev.ingredient_id, {}).get('order', 99),
                'concentration': pi_map.get(ev.ingredient_id, {}).get('concentration', ''),
            }
            parent_map[parent_obj.id].setdefault(child_obj.id, {
                '_concern': child_obj,
                'ingredients': {},
            })
            existing = parent_map[parent_obj.id][child_obj.id]['ingredients'].get(ev.ingredient_id)
            tier_rank = {'well_founded': 3, 'studied': 2, 'prospective': 1}
            if not existing or tier_rank.get(ev.evidence_tier, 0) > tier_rank.get(existing.get('tier'), 0):
                parent_map[parent_obj.id][child_obj.id]['ingredients'][ev.ingredient_id] = entry

        # Format output
        result = []
        for parent_id, sub_data in parent_map.items():
            parent_obj = sub_data.pop('_parent')
            sub_concerns = []
            for sub_key, sub_info in sub_data.items():
                concern_obj = sub_info['_concern']
                ingredients = sorted(
                    sub_info['ingredients'].values(),
                    key=lambda x: -({'well_founded': 3, 'studied': 2, 'prospective': 1}.get(x['tier'], 0)),
                )
                if ingredients:
                    sub_concerns.append({
                        'concern': {
                            'id': concern_obj.id,
                            'label': concern_obj.label,
                            'internal_key': concern_obj.internal_key,
                        },
                        'ingredients': [
                            {
                                'id': ing['ingredient_id'],
                                'inci_name': ing['inci_name'],
                                'tier': ing['tier'],
                                'count': ing['count'],
                                'articles': ing['articles'],
                                'query_used': ing.get('query_used', ''),
                                'order': ing.get('order', 99),
                                'concentration': ing.get('concentration', ''),
                            }
                            for ing in ingredients
                        ],
                    })
            if sub_concerns:
                result.append({
                    'parent': {
                        'id': parent_obj.id,
                        'label': parent_obj.label,
                        'internal_key': parent_obj.internal_key,
                    },
                    'sub_concerns': sub_concerns,
                })

        return result


# ── Routine (Phase 2) ───────────────────────────────────────────────────────

class RoutineItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = RoutineItem
        fields = ['id', 'product', 'product_id', 'step_order']


class RoutineSerializer(serializers.ModelSerializer):
    items = RoutineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Routine
        fields = ['id', 'name', 'time_of_day', 'items', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ── Analytics ────────────────────────────────────────────────────────────────

class ClickEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClickEvent
        fields = ['id', 'product', 'retailer_listing', 'source_page', 'clicked_at']
        read_only_fields = ['clicked_at']
