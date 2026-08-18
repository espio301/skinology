from django.conf import settings
from django.db import models


class ClickEvent(models.Model):
    """
    Tracks affiliate link clicks. Powers CTR metrics and brand data sales.
    User is nullable — anonymous visitors can still generate click events.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='click_events',
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='click_events',
    )
    retailer_listing = models.ForeignKey(
        'RetailerListing',
        on_delete=models.CASCADE,
        related_name='click_events',
    )
    source_page = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Page URL where the click originated'
    )
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-clicked_at']
        verbose_name = 'Click Event'
        verbose_name_plural = 'Click Events'

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f'{user_str} → {self.product.name} @ {self.clicked_at:%Y-%m-%d %H:%M}'
