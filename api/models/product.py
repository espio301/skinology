from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    """
    A skincare product. Linked to ingredients via ProductIngredient and
    tagged with skin concerns it helps address.
    """
    PRODUCT_TYPES = [
        ('cleanser', 'Cleanser'),
        ('toner', 'Toner'),
        ('serum', 'Serum'),
        ('moisturizer', 'Moisturizer'),
        ('sunscreen', 'Sunscreen'),
        ('exfoliant', 'Exfoliant'),
        ('mask', 'Mask'),
        ('eye_cream', 'Eye Cream'),
        ('oil', 'Oil'),
        ('treatment', 'Treatment'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=400)
    brand = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=500, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    image_url = models.URLField(max_length=1000, blank=True, default='')
    product_type = models.CharField(
        max_length=50,
        choices=PRODUCT_TYPES,
        default='other',
        db_index=True,
    )
    avg_ph = models.FloatField(
        null=True,
        blank=True,
        help_text='Average pH level of the product'
    )
    raw_inci = models.JSONField(
        default=list,
        blank=True,
        help_text='Full ordered INCI ingredient list as scraped'
    )
    concerns = models.ManyToManyField(
        'SkinConcern',
        related_name='products',
        blank=True,
        help_text='Skin concerns this product addresses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.brand} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f'{self.brand}-{self.name}')
            slug = base_slug
            n = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ProductIngredient(models.Model):
    """
    Through-model linking a Product to an Ingredient.
    Tracks INCI order (proxy for concentration) and optional concentration %.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_ingredients',
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        related_name='product_ingredients',
    )
    order = models.PositiveIntegerField(
        help_text='Position in INCI list (1 = highest concentration)'
    )
    concentration = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Optional concentration, e.g. "2%"'
    )

    class Meta:
        ordering = ['order']
        unique_together = ['product', 'ingredient']
        verbose_name = 'Product Ingredient'
        verbose_name_plural = 'Product Ingredients'

    def __str__(self):
        return f'{self.product.name} — {self.ingredient} (#{self.order})'
