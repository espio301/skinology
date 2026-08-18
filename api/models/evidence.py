from django.db import models


class IngredientConcernEvidence(models.Model):
    """
    Through-model linking Ingredient ↔ SkinConcern with PubMed evidence data.
    Stores the article count and computed evidence tier for each pair.
    """
    TIER_CHOICES = [
        ('well_founded', 'Well Founded'),   # green  — ≥200 results
        ('studied', 'Studied'),              # yellow — 50–199
        ('prospective', 'Prospective'),      # orange — <50
    ]

    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        related_name='evidence_scores',
    )
    concern = models.ForeignKey(
        'SkinConcern',
        on_delete=models.CASCADE,
        related_name='evidence_scores',
    )
    pubmed_count = models.IntegerField(default=0)
    evidence_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='prospective',
    )
    query_used = models.TextField(
        blank=True,
        default='',
        help_text='Stored PubMed query string for debugging/auditing',
    )
    top_articles = models.JSONField(
        default=list,
        blank=True,
        help_text='Top PubMed articles, e.g. [{"pmid": "12345", "title": "...", "year": "2023"}]',
    )
    last_queried = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('ingredient', 'concern')
        verbose_name = 'Ingredient-Concern Evidence'
        verbose_name_plural = 'Ingredient-Concern Evidence'

    def __str__(self):
        return f'{self.ingredient} × {self.concern} → {self.evidence_tier} ({self.pubmed_count})'
