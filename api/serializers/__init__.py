from rest_framework import serializers
from api.models import (
    Ingredient, IngredientUmbrella, SkinConcern, Product, ProductIngredient,
    Retailer, RetailerListing, UserProfile, Routine, RoutineItem,
    ClickEvent, Article,
)


# ── Ingredient & Science ────────────────────────────────────────────────────

class IngredientUmbrellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientUmbrella
        fields = ['id', 'name', 'description']


class SkinConcernSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkinConcern
        fields = ['id', 'label', 'internal_key', 'description']


class IngredientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ingredient lists."""
    umbrellas = IngredientUmbrellaSerializer(many=True, read_only=True)

    class Meta:
        model = Ingredient
        fields = ['id', 'inci_name', 'common_name', 'umbrellas']


class IngredientDetailSerializer(serializers.ModelSerializer):
    """Full serializer with science summary and linked articles."""
    umbrellas = IngredientUmbrellaSerializer(many=True, read_only=True)
    concerns_supported = SkinConcernSerializer(many=True, read_only=True)
    articles = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = [
            'id', 'inci_name', 'common_name', 'description',
            'science_summary', 'synonyms', 'umbrellas',
            'concerns_supported', 'articles',
        ]

    def get_articles(self, obj):
        return ArticleSerializer(obj.articles.all(), many=True).data


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'url', 'source', 'summary', 'published_date']


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

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'slug', 'image_url',
            'product_type', 'concerns', 'min_price',
        ]

    def get_min_price(self, obj):
        listing = obj.retailer_listings.filter(in_stock=True).order_by('price').first()
        return str(listing.price) if listing and listing.price else None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer with ingredients, listings, and concerns."""
    concerns = SkinConcernSerializer(many=True, read_only=True)
    product_ingredients = ProductIngredientSerializer(many=True, read_only=True)
    retailer_listings = RetailerListingSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'slug', 'description', 'image_url',
            'product_type', 'avg_ph', 'raw_inci', 'concerns',
            'product_ingredients', 'retailer_listings',
            'created_at', 'updated_at',
        ]


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
