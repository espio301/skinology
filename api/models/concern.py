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
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        help_text='Parent concern for sub-concern hierarchy'
    )
    description = models.TextField(blank=True, default='')
    pubmed_terms = models.JSONField(
        default=list,
        blank=True,
        help_text='PubMed search terms, e.g. [{"term": "Skin Aging", "field": "Mesh"}, {"term": "photoaging", "field": "tiab"}]'
    )
    pubmed_excluders = models.JSONField(
        default=list,
        blank=True,
        help_text='PubMed exclusion terms, e.g. [{"term": "Alopecia", "field": "Mesh"}, {"term": "hair", "field": "tiab"}]'
    )

    class Meta:
        ordering = ['label']
        verbose_name = 'Skin Concern'
        verbose_name_plural = 'Skin Concerns'

    def __str__(self):
        return self.label
