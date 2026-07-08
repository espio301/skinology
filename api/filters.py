import django_filters
from api.models import Product, Ingredient


class ProductFilter(django_filters.FilterSet):
    """
    Filterset for products. Supports concern-based, ingredient umbrella-based,
    pH range, price range, brand, and product type filtering.
    """
    concerns = django_filters.BaseInFilter(
        field_name='concerns__id',
        lookup_expr='in',
        label='Concern IDs (comma-separated)',
    )
    brand = django_filters.CharFilter(
        field_name='brand',
        lookup_expr='iexact',
    )
    product_type = django_filters.CharFilter(
        field_name='product_type',
        lookup_expr='exact',
    )
    ph_min = django_filters.NumberFilter(
        field_name='avg_ph',
        lookup_expr='gte',
        label='Minimum pH',
    )
    ph_max = django_filters.NumberFilter(
        field_name='avg_ph',
        lookup_expr='lte',
        label='Maximum pH',
    )
    ingredient_umbrella = django_filters.CharFilter(
        method='filter_by_umbrella',
        label='Ingredient umbrella name',
    )
    price_min = django_filters.NumberFilter(
        method='filter_price_min',
        label='Minimum price',
    )
    price_max = django_filters.NumberFilter(
        method='filter_price_max',
        label='Maximum price',
    )

    class Meta:
        model = Product
        fields = ['concerns', 'brand', 'product_type']

    def filter_by_umbrella(self, queryset, name, value):
        return queryset.filter(
            product_ingredients__ingredient__umbrellas__name__iexact=value
        ).distinct()

    def filter_price_min(self, queryset, name, value):
        return queryset.filter(
            retailer_listings__price__gte=value,
            retailer_listings__in_stock=True,
        ).distinct()

    def filter_price_max(self, queryset, name, value):
        return queryset.filter(
            retailer_listings__price__lte=value,
            retailer_listings__in_stock=True,
        ).distinct()


class IngredientFilter(django_filters.FilterSet):
    """Filter ingredients by umbrella category or supported concern."""
    umbrella = django_filters.CharFilter(
        field_name='umbrellas__name',
        lookup_expr='iexact',
    )
    concern = django_filters.NumberFilter(
        field_name='concerns_supported__id',
        lookup_expr='exact',
    )

    class Meta:
        model = Ingredient
        fields = ['umbrella', 'concern']
