"""
Celery tasks for PubMed evidence scoring.

Schedule via django-celery-beat in the admin or by adding a
PeriodicTask pointing at 'api.tasks.update_pubmed_evidence'.
"""
from celery import shared_task
from django.core.management import call_command


@shared_task
def update_pubmed_evidence():
    """Daily task to refresh PubMed evidence scores for all ingredient–concern pairs."""
    call_command('update_evidence')
