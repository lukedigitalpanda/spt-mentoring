"""
Management command to generate VAPID key pair for Web Push notifications.
Run once: python manage.py generate_vapid_keys
Then add the output to your .env file.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate VAPID public/private key pair for Web Push notifications'

    def handle(self, *args, **options):
        try:
            from py_vapid import Vapid
        except ImportError:
            self.stderr.write("py_vapid not available; generating via pywebpush...")
            from pywebpush import Vapid as Vapid

        vapid = Vapid()
        vapid.generate_keys()
        private_key = vapid.private_pem().decode('utf-8').strip()
        public_key = vapid.public_key.get_uncompressed_point().hex()

        self.stdout.write(self.style.SUCCESS('\n=== VAPID Keys Generated ===\n'))
        self.stdout.write(f'VAPID_PUBLIC_KEY={public_key}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={private_key}')
        self.stdout.write(self.style.WARNING(
            '\nAdd these to your .env file, then set VITE_VAPID_PUBLIC_KEY in the frontend.\n'
        ))
