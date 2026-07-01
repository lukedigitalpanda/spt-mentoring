from django.core.management.base import BaseCommand

from apps.notifications.email_catalogue import EMAIL_CATALOGUE
from apps.notifications.models import EmailCatalogueEntry


class Command(BaseCommand):
    help = 'Rebuild the EmailCatalogueEntry table from email_catalogue.EMAIL_CATALOGUE.'

    def handle(self, *args, **options):
        keys = set()
        for spec in EMAIL_CATALOGUE:
            keys.add(spec.key)
            EmailCatalogueEntry.objects.update_or_create(
                key=spec.key,
                defaults=dict(
                    name=spec.name, trigger=spec.trigger, recipients=spec.recipients,
                    subject=spec.subject, body=spec.body, debounced=spec.debounced,
                    source=spec.source, notes=spec.notes,
                ),
            )
        removed, _ = EmailCatalogueEntry.objects.exclude(key__in=keys).delete()
        self.stdout.write(self.style.SUCCESS(
            f'Synced {len(EMAIL_CATALOGUE)} catalogue entries ({removed} stale removed).'))
