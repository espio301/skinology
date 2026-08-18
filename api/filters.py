import django_filters
from api.models import Product, Ingredient


class ProductFilter(django_filters.FilterSet):
    """
    Filterset for products. Supports concern-based, ingredient umbrella-based,
    pH range, price range, brand, and product type filtering.
    """
    concerns = django_filters.CharFilter(
        method='filter_by_concerns',
        label='Concern IDs or internal keys (comma-separated)',
    )
    brand = django_filters.CharFilter(
        field_name='brand',
        lookup_expr='iexact',
    )
    product_type = django_filters.BaseInFilter(
        field_name='product_type',
        lookup_expr='in',
        label='Product types (comma-separated)',
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
    strength = django_filters.BaseInFilter(
        field_name='strength',
        lookup_expr='in',
        label='Strength tiers (comma-separated)',
    )
    search = django_filters.CharFilter(
        method='filter_by_search',
        label='Search by product name or brand',
    )

    class Meta:
        model = Product
        fields = ['concerns', 'brand', 'product_type', 'strength', 'search']

    def filter_by_search(self, queryset, name, value):
        if not value:
            return queryset
        from django.db import models
        term = value.strip()
        return queryset.filter(
            models.Q(name__icontains=term) | models.Q(brand__icontains=term)
        )

    def filter_by_concerns(self, queryset, name, value):
        if not value:
            return queryset
        from django.db import models
        keys = [k.strip() for k in value.split(',') if k.strip()]
        numeric_ids = [int(k) for k in keys if k.isdigit()]
        string_keys = [k for k in keys if not k.isdigit()]

        q_objects = models.Q()
        if numeric_ids:
            q_objects |= models.Q(concerns__id__in=numeric_ids)
        if string_keys:
            q_objects |= models.Q(concerns__internal_key__in=string_keys)
            q_objects |= models.Q(concerns__parent__internal_key__in=string_keys)

        return queryset.filter(q_objects).distinct()

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
    """Filter ingredients by umbrella category, supported concern, or PubMed evidence presence."""
    umbrella = django_filters.CharFilter(
        field_name='umbrellas__name',
        lookup_expr='iexact',
    )
    concern = django_filters.NumberFilter(
        field_name='concerns_supported__id',
        lookup_expr='exact',
    )
    has_evidence = django_filters.BooleanFilter(
        method='filter_has_evidence',
        label='Only ingredients with PubMed evidence',
    )

    class Meta:
        model = Ingredient
        fields = ['umbrella', 'concern', 'has_evidence']

    def filter_has_evidence(self, queryset, name, value):
        if not value:
            return queryset
        from django.db import models
        return queryset.filter(
            models.Q(evidence_scores__pubmed_count__gt=0) | models.Q(articles__isnull=False)
        ).distinct()
