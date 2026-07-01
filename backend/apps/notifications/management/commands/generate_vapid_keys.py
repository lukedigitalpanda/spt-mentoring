"""
Management command to generate VAPID key pair for Web Push notifications.
Run once: python manage.py generate_vapid_keys
Then add the output to your .env file.

Output format:
  VAPID_PRIVATE_KEY — base64url raw EC private value (accepted by pywebpush)
  VAPID_PUBLIC_KEY  — base64url uncompressed P-256 point (used by the browser
                      as applicationServerKey / VITE_VAPID_PUBLIC_KEY)
"""
import base64

from django.core.management.base import BaseCommand


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


class Command(BaseCommand):
    help = 'Generate VAPID public/private key pair for Web Push notifications'

    def handle(self, *args, **options):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        private_raw = key.private_numbers().private_value.to_bytes(32, 'big')
        public_raw = key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

        self.stdout.write(self.style.SUCCESS('\n=== VAPID Keys Generated ===\n'))
        self.stdout.write(f'VAPID_PUBLIC_KEY={_b64url(public_raw)}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={_b64url(private_raw)}')
        self.stdout.write(self.style.WARNING(
            '\nAdd these to your .env file. The public key must also be passed to '
            'the frontend build as VITE_VAPID_PUBLIC_KEY (docker-compose does this '
            'automatically from VAPID_PUBLIC_KEY).\n'
        ))
