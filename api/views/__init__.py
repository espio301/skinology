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
    queryset = SkinConcern.objects.all()
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
