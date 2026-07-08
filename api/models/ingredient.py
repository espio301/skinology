from django.db import models


class IngredientUmbrella(models.Model):
    """
    Broad grouping for ingredients, e.g. 'Retinoids', 'AHAs', 'Growth Factors'.
    Lets users filter by category while individual ingredients hold the specifics.
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Ingredient Umbrellas'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    A single skincare ingredient identified by its canonical INCI name.
    Linked to one or more umbrella categories and may have multiple synonyms.
    """
    inci_name = models.CharField(
        max_length=300,
        unique=True,
        help_text='Canonical INCI name, e.g. Retinol'
    )
    common_name = models.CharField(
        max_length=300,
        blank=True,
        default='',
        help_text='User-friendly common name'
    )
    description = models.TextField(blank=True, default='')
    science_summary = models.TextField(
        blank=True,
        default='',
        help_text='Summary of peer-reviewed evidence'
    )
    synonyms = models.JSONField(
        default=list,
        blank=True,
        help_text='List of alternate names for synonym resolution'
    )
    umbrellas = models.ManyToManyField(
        IngredientUmbrella,
        related_name='ingredients',
        blank=True,
        help_text='Umbrella categories this ingredient belongs to'
    )
    concerns_supported = models.ManyToManyField(
        'SkinConcern',
        related_name='supporting_ingredients',
        blank=True,
        help_text='Skin concerns this ingredient helps address'
    )

    class Meta:
        ordering = ['inci_name']

    def __str__(self):
        return self.common_name or self.inci_name
