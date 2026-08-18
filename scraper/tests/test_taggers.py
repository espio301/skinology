"""
Unit tests for the concern auto-tagger.
"""

from django.test import TestCase

from api.models import (
    Ingredient,
    Product,
    ProductIngredient,
    SkinConcern,
)
from scraper.taggers import auto_tag_product, auto_tag_all_products


class AutoTagProductTest(TestCase):
    """Tests for ``auto_tag_product``."""

    def setUp(self):
        """Create shared fixtures."""
        # Concerns
        self.acne, _ = SkinConcern.objects.get_or_create(
            internal_key="acne",
            defaults={"label": "Test Blemish Skin"}
        )
        self.aging, _ = SkinConcern.objects.get_or_create(
            internal_key="aging",
            defaults={"label": "Test Anti Aging"}
        )
        self.dryness, _ = SkinConcern.objects.get_or_create(
            internal_key="dryness",
            defaults={"label": "Test Dryness"}
        )

        # Ingredients with concern links
        self.retinol = Ingredient.objects.create(inci_name="Retinol")
        self.retinol.concerns_supported.add(self.aging)

        self.salicylic = Ingredient.objects.create(inci_name="Salicylic Acid")
        self.salicylic.concerns_supported.add(self.acne)

        self.glycerin = Ingredient.objects.create(inci_name="Glycerin")
        self.glycerin.concerns_supported.add(self.dryness)

        self.water = Ingredient.objects.create(inci_name="Water")
        # Water has no concern links

    def test_tags_product_with_single_concern(self):
        product = Product.objects.create(name="Retinol Serum", brand="TestCo")
        ProductIngredient.objects.create(
            product=product, ingredient=self.retinol, order=1
        )

        auto_tag_product(product)

        concerns = set(product.concerns.values_list("internal_key", flat=True))
        self.assertEqual(concerns, {"aging"})

    def test_tags_product_with_multiple_concerns(self):
        product = Product.objects.create(name="Multi-Active", brand="TestCo")
        ProductIngredient.objects.create(
            product=product, ingredient=self.retinol, order=1
        )
        ProductIngredient.objects.create(
            product=product, ingredient=self.salicylic, order=2
        )
        ProductIngredient.objects.create(
            product=product, ingredient=self.glycerin, order=3
        )

        auto_tag_product(product)

        concerns = set(product.concerns.values_list("internal_key", flat=True))
        self.assertTrue(concerns.issubset({"aging", "acne", "dryness", "acne-blemishes", "hydration-barrier"}))
        self.assertTrue(len(concerns) >= 2)

    def test_clears_concerns_when_no_match(self):
        product = Product.objects.create(name="Plain Water", brand="TestCo")
        product.concerns.add(self.acne)  # manually add a concern

        ProductIngredient.objects.create(
            product=product, ingredient=self.water, order=1
        )

        auto_tag_product(product)

        self.assertEqual(product.concerns.count(), 0)

    def test_no_ingredients_clears_concerns(self):
        product = Product.objects.create(name="Empty", brand="TestCo")
        product.concerns.add(self.aging)

        auto_tag_product(product)

        self.assertEqual(product.concerns.count(), 0)

    def test_idempotent(self):
        product = Product.objects.create(name="Idempotent", brand="TestCo")
        ProductIngredient.objects.create(
            product=product, ingredient=self.retinol, order=1
        )

        auto_tag_product(product)
        auto_tag_product(product)  # second call

        self.assertEqual(product.concerns.count(), 1)


class AutoTagAllProductsTest(TestCase):
    """Tests for ``auto_tag_all_products``."""

    def test_tags_multiple_products(self):
        aging = SkinConcern.objects.create(
            label="Fine Lines", internal_key="aging"
        )
        retinol = Ingredient.objects.create(inci_name="Retinol")
        retinol.concerns_supported.add(aging)

        p1 = Product.objects.create(name="Serum A", brand="BrandA")
        ProductIngredient.objects.create(
            product=p1, ingredient=retinol, order=1
        )
        p2 = Product.objects.create(name="Serum B", brand="BrandB")
        ProductIngredient.objects.create(
            product=p2, ingredient=retinol, order=1
        )

        count = auto_tag_all_products()

        self.assertEqual(count, 2)
        self.assertEqual(p1.concerns.count(), 1)
        self.assertEqual(p2.concerns.count(), 1)
