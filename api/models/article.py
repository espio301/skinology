from django.db import models


class Article(models.Model):
    """
    A peer-reviewed or science-backed article.
    Linked to ingredients to provide evidence for their efficacy.
    """
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000, unique=True)
    source = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='e.g. PubMed, Journal of Dermatology'
    )
    summary = models.TextField(blank=True, default='')
    ingredients = models.ManyToManyField(
        'Ingredient',
        related_name='articles',
        blank=True,
        help_text='Ingredients discussed in this article'
    )
    published_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title
