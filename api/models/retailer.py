from django.db import models


class Retailer(models.Model):
    """
    A retailer where products can be purchased (Sephora, Ulta, Amazon, etc.).
    """
    AFFILIATE_NETWORKS = [
        ('sovrn', 'Sovrn'),
        ('amazon_associates', 'Amazon Associates'),
        ('direct', 'Direct / None'),
    ]

    name = models.CharField(max_length=200, unique=True)
    base_url = models.URLField(max_length=500)
    affiliate_network = models.CharField(
        max_length=50,
        choices=AFFILIATE_NETWORKS,
        default='sovrn',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class RetailerListing(models.Model):
    """
    A specific product listing at a specific retailer.
    Tracks price, stock status, and affiliate URL separately from the product itself.
    """
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='retailer_listings',
    )
    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name='listings',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, default='USD')
    product_url = models.URLField(max_length=1000)
    affiliate_url = models.URLField(
        max_length=1000,
        blank=True,
        default='',
        help_text='Sovrn/affiliate-wrapped URL'
    )
    in_stock = models.BooleanField(default=True)
    last_scraped = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'retailer']
        ordering = ['price']
        verbose_name = 'Retailer Listing'
        verbose_name_plural = 'Retailer Listings'

    def __str__(self):
        return f'{self.product.name} @ {self.retailer.name} — ${self.price}'
