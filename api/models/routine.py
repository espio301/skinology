from django.conf import settings
from django.db import models


class Routine(models.Model):
    """
    A user's skincare routine (e.g. 'Morning Routine', 'Night Routine').
    Phase 2 feature — included in models now for schema completeness.
    """
    TIME_CHOICES = [
        ('AM', 'Morning'),
        ('PM', 'Evening'),
        ('BOTH', 'Both'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routines',
    )
    name = models.CharField(max_length=200, default='My Routine')
    time_of_day = models.CharField(
        max_length=4,
        choices=TIME_CHOICES,
        default='AM',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.name}'


class RoutineItem(models.Model):
    """
    A single step in a routine, linking to a specific product.
    """
    routine = models.ForeignKey(
        Routine,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='routine_items',
    )
    step_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['step_order']
        unique_together = ['routine', 'product']
        verbose_name = 'Routine Item'
        verbose_name_plural = 'Routine Items'

    def __str__(self):
        return f'Step {self.step_order}: {self.product.name}'
