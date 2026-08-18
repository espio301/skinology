from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from api.models import (
    Product, Ingredient, IngredientUmbrella, SkinConcern,
    Retailer, RetailerListing, Article,
    Routine, RoutineItem, ClickEvent,
)
from api.serializers import (
    ProductListSerializer, ProductDetailSerializer,
    IngredientListSerializer, IngredientDetailSerializer,
    IngredientUmbrellaSerializer, SkinConcernSerializer,
    ArticleSerializer, RetailerListingSerializer,
    RoutineSerializer, RoutineItemSerializer,
    ClickEventSerializer,
)
from api.filters import ProductFilter, IngredientFilter


# ── Products ─────────────────────────────────────────────────────────────────

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:   GET /api/products/          — search & filter products
    detail: GET /api/products/{slug}/   — full product detail
    buy:    GET /api/products/{slug}/buy/?retailer={id}  — redirect via affiliate
    """
    queryset = Product.objects.prefetch_related(
        'concerns', 'retailer_listings__retailer',
        'product_ingredients__ingredient__umbrellas',
    ).all()
    lookup_field = 'slug'
    filterset_class = ProductFilter
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['name', 'brand', 'created_at']

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        priority_param = self.request.query_params.get('concern_priority') or self.request.query_params.get('concerns')
        if priority_param:
            priority_keys = [k.strip() for k in priority_param.split(',') if k.strip()]
            if priority_keys:
                qs = self.apply_priority_sorting(qs, priority_keys)
        return qs

    def apply_priority_sorting(self, qs, priority_keys):
        """
        Multi-factor relevance scoring for concern-based product sorting.

        For each product, we compute a relevance score based ONLY on
        ingredients that have PubMed evidence for the SELECTED concern(s).

        Score = sum of (potency × evidence_weight) for matching ingredients,
        taking the best score per concern.

        Only ingredients in INGREDIENT_POTENCY_MAP contribute. Unknown
        filler/base ingredients score 0 so they never inflate rankings.
        """
        import re
        from django.db import models
        from api.models import IngredientConcernEvidence, ProductIngredient
        from scraper.parsers.ingredient_properties import INGREDIENT_POTENCY_MAP

        concerns = list(SkinConcern.objects.filter(
            models.Q(id__in=[k for k in priority_keys if k.isdigit()]) |
            models.Q(internal_key__in=priority_keys)
        ))
        if not concerns:
            return qs

        # Collect all concern IDs: selected parents + their children
        selected_concern_ids = set()
        for c in concerns:
            selected_concern_ids.add(c.id)
            for child in c.children.all():
                selected_concern_ids.add(child.id)

        # Map priority keys to their user-specified priority index
        key_order = {}
        for idx, k in enumerate(priority_keys):
            key_order[k] = idx
            if k.isdigit():
                c = next((c for c in concerns if str(c.id) == k), None)
                if c:
                    key_order[c.internal_key] = idx

        product_list = list(qs)
        if not product_list:
            return qs

        k_count = len(priority_keys)

        # Evidence tier → multiplier
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

        def parse_concentration(conc_str):
            """Extract numeric concentration from strings like '5%', '0.5%'."""
            if not conc_str:
                return None
            m = re.search(r'(\d+(?:\.\d+)?)\s*%', conc_str)
            return float(m.group(1)) if m else None

        def get_potency_score(inci_name, concentration_pct=None):
            """Look up base potency. Unknown ingredients return 0."""
            entry = INGREDIENT_POTENCY_MAP.get(inci_name)
            if not entry:
                return 0  # Unknown ingredients do NOT contribute
            base = entry['base']
            if concentration_pct is not None and 'conc_boost' in entry:
                for threshold in sorted(entry['conc_boost'].keys(), reverse=True):
                    if concentration_pct >= threshold:
                        return entry['conc_boost'][threshold]
            return base

        def calc_score(product):
            pi_list = list(product.product_ingredients.select_related('ingredient').all())
            if not pi_list:
                return (0, 0, 0)

            # Build lookup maps: ingredient_id → (order, inci_name, concentration)
            pi_map = {}
            for pi in pi_list:
                pi_map[pi.ingredient_id] = {
                    'order': pi.order,
                    'inci_name': pi.ingredient.inci_name,
                    'concentration': pi.concentration,
                }

            # Fetch evidence for the SELECTED concern(s) and their children.
            # Include rows with pubmed_count=0 — these come from curated
            # CONCERN_INGREDIENT_MAP and still indicate a valid association.
            ev_qs = IngredientConcernEvidence.objects.filter(
                ingredient_id__in=pi_map.keys(),
                concern_id__in=selected_concern_ids,
            ).select_related('concern', 'concern__parent')

            # Sum the relevance of ALL matching ingredients (not just best).
            # This rewards products with MULTIPLE concern-relevant actives.
            total_relevance = 0
            # Track the best evidence weight per ingredient (an ingredient
            # may appear in multiple evidence rows across sub-concerns).
            best_per_ingredient = {}  # ingredient_id → best (potency, ev_weight)

            for ev in ev_qs:
                ing_info = pi_map.get(ev.ingredient_id)
                if not ing_info:
                    continue

                # Factor 1: Intrinsic potency (0–10, including active conc_boost)
                conc_pct = parse_concentration(ing_info['concentration'])
                potency = get_potency_score(ing_info['inci_name'], conc_pct)

                if potency == 0:
                    continue  # Skip unknown/filler ingredients entirely

                # Factor 2: Evidence weight (1.0–3.0)
                ev_weight = EVIDENCE_MULTIPLIER.get(ev.evidence_tier, 1.0)

                # Keep the best score per ingredient across sub-concerns
                ing_id = ev.ingredient_id
                current_score = potency * ev_weight
                prev = best_per_ingredient.get(ing_id, 0)
                if current_score > prev:
                    best_per_ingredient[ing_id] = current_score

            total_relevance = sum(best_per_ingredient.values())

            strength_score = STRENGTH_RANK.get(product.strength, 1)
            rating_score = float(product.review_rating or 0)

            return (total_relevance, strength_score, rating_score)

        product_list.sort(key=calc_score, reverse=True)
        p_ids = [p.id for p in product_list]
        clauses = ' '.join([f"WHEN id={pid} THEN {idx}" for idx, pid in enumerate(p_ids)])
        return Product.objects.filter(id__in=p_ids).extra(
            select={'priority_rank': f"CASE {clauses} END"},
            order_by=['priority_rank']
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['get'], url_path='buy')
    def buy(self, request, slug=None):
        """
        Log a ClickEvent and return the affiliate URL for redirect.
        Query param: ?retailer={retailer_id}
        """
        product = self.get_object()
        retailer_id = request.query_params.get('retailer')

        if not retailer_id:
            # Default to first available in-stock listing
            listing = product.retailer_listings.filter(in_stock=True).first()
        else:
            listing = get_object_or_404(
                RetailerListing, product=product, retailer_id=retailer_id
            )

        if not listing:
            return Response(
                {'error': 'No available listing found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Log click event
        ClickEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            product=product,
            retailer_listing=listing,
            source_page=request.query_params.get('source', ''),
        )

        redirect_url = listing.affiliate_url or listing.product_url
        return Response({'affiliate_url': redirect_url})


# ── Ingredients & Science ────────────────────────────────────────────────────

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.prefetch_related(
        'umbrellas', 'concerns_supported', 'articles',
    ).all()
    filterset_class = IngredientFilter
    search_fields = ['inci_name', 'common_name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return IngredientDetailSerializer
        return IngredientListSerializer


class SkinConcernViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SkinConcern.objects.filter(parent__isnull=True).order_by('id')
    serializer_class = SkinConcernSerializer


class IngredientUmbrellaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IngredientUmbrella.objects.all()
    serializer_class = IngredientUmbrellaSerializer


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.prefetch_related('ingredients').all()
    serializer_class = ArticleSerializer
    search_fields = ['title', 'summary']


# ── Routines (Phase 2) ──────────────────────────────────────────────────────

class RoutineViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Routine.objects.filter(user=self.request.user).prefetch_related(
            'items__product__concerns',
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RoutineItemViewSet(viewsets.ModelViewSet):
    serializer_class = RoutineItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RoutineItem.objects.filter(
            routine__user=self.request.user,
            routine_id=self.kwargs.get('routine_pk'),
        )

    def perform_create(self, serializer):
        routine = get_object_or_404(
            Routine, pk=self.kwargs['routine_pk'], user=self.request.user
        )
        serializer.save(routine=routine)


# ── Analytics ────────────────────────────────────────────────────────────────

class ClickEventCreateView(generics.CreateAPIView):
    """POST /api/events/click/ — log an affiliate click."""
    serializer_class = ClickEventSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
