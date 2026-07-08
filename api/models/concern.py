from django.db import models


class SkinConcern(models.Model):
    """
    A skin concern tagged with user-friendly language.
    - label: what users see, e.g. 'Visible Redness', 'Blemish-Prone Skin'
    - internal_key: backend reference, e.g. 'rosacea', 'acne'
    """
    label = models.CharField(
        max_length=200,
        unique=True,
        help_text='User-facing label, e.g. "Visible Redness"'
    )
    internal_key = models.SlugField(
        max_length=100,
        unique=True,
        help_text='Internal key for backend logic, e.g. "rosacea"'
    )
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['label']
        verbose_name = 'Skin Concern'
        verbose_name_plural = 'Skin Concerns'

    def __str__(self):
        return self.label
