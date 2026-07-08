from django.contrib import admin
from api.models import (
    Product, Ingredient, IngredientUmbrella, SkinConcern,
    ProductIngredient, Retailer, RetailerListing,
    UserProfile, Routine, RoutineItem, ClickEvent, Article,
)


class ProductIngredientInline(admin.TabularInline):
    model = ProductIngredient
    extra = 1
    autocomplete_fields = ['ingredient']


class RetailerListingInline(admin.TabularInline):
    model = RetailerListing
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'product_type', 'avg_ph', 'updated_at']
    list_filter = ['product_type', 'brand', 'concerns']
    search_fields = ['name', 'brand']
    prepopulated_fields = {'slug': ('brand', 'name')}
    inlines = [ProductIngredientInline, RetailerListingInline]
    filter_horizontal = ['concerns']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['inci_name', 'common_name']
    search_fields = ['inci_name', 'common_name']
    filter_horizontal = ['umbrellas', 'concerns_supported']


@admin.register(IngredientUmbrella)
class IngredientUmbrellaAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(SkinConcern)
class SkinConcernAdmin(admin.ModelAdmin):
    list_display = ['label', 'internal_key']
    search_fields = ['label', 'internal_key']


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ['name', 'affiliate_network']


@admin.register(RetailerListing)
class RetailerListingAdmin(admin.ModelAdmin):
    list_display = ['product', 'retailer', 'price', 'in_stock', 'last_scraped']
    list_filter = ['retailer', 'in_stock']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'skin_type']
    list_filter = ['skin_type']


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'time_of_day', 'created_at']
    list_filter = ['time_of_day']


@admin.register(RoutineItem)
class RoutineItemAdmin(admin.ModelAdmin):
    list_display = ['routine', 'product', 'step_order']


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'retailer_listing', 'clicked_at']
    list_filter = ['clicked_at']
    date_hierarchy = 'clicked_at'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'published_date']
    search_fields = ['title', 'summary']
    filter_horizontal = ['ingredients']
