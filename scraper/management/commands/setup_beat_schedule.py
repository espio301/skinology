"""
Management command to seed ``django-celery-beat`` periodic tasks.

Usage::

    python manage.py setup_beat_schedule

Idempotent — safe to run multiple times; existing schedules are updated.
"""

import json

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Create / update Celery Beat periodic task schedules for the scraper pipeline."

    SCHEDULES = [
        {
            "name": "scraper.discover_new_products (daily 3 AM UTC)",
            "task": "scraper.tasks.discover_new_products",
            "crontab": {"minute": "0", "hour": "3"},
        },
        {
            "name": "scraper.refresh_prices (8 AM UTC)",
            "task": "scraper.tasks.refresh_prices",
            "crontab": {"minute": "0", "hour": "8"},
        },
        {
            "name": "scraper.refresh_prices (8 PM UTC)",
            "task": "scraper.tasks.refresh_prices",
            "crontab": {"minute": "0", "hour": "20"},
        },
    ]

    def handle(self, *args, **options):
        for entry in self.SCHEDULES:
            crontab_kwargs = {
                "minute": entry["crontab"].get("minute", "*"),
                "hour": entry["crontab"].get("hour", "*"),
                "day_of_week": entry["crontab"].get("day_of_week", "*"),
                "day_of_month": entry["crontab"].get("day_of_month", "*"),
                "month_of_year": entry["crontab"].get("month_of_year", "*"),
            }

            schedule, _ = CrontabSchedule.objects.get_or_create(**crontab_kwargs)

            task, created = PeriodicTask.objects.update_or_create(
                name=entry["name"],
                defaults={
                    "task": entry["task"],
                    "crontab": schedule,
                    "kwargs": json.dumps({}),
                    "enabled": True,
                },
            )

            status = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  {status}: {entry['name']}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone — {len(self.SCHEDULES)} periodic tasks configured."
            )
        )
