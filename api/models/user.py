from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """
    Extended profile for users. One-to-one with Django's built-in User model.
    Stores skincare-specific preferences.
    """
    SKIN_TYPES = [
        ('oily', 'Oily'),
        ('dry', 'Dry'),
        ('combination', 'Combination'),
        ('normal', 'Normal'),
        ('sensitive', 'Sensitive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    skin_type = models.CharField(
        max_length=20,
        choices=SKIN_TYPES,
        blank=True,
        default='',
    )
    skin_concerns = models.ManyToManyField(
        'SkinConcern',
        related_name='users',
        blank=True,
        help_text='Skin concerns the user has identified'
    )

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'Profile: {self.user.username}'
