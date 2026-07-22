"""JaaS (8x8) join-URL minting.

Builds a short-lived RS256 JWT per participant so the backend can grant
moderator rights without the public meet.jit.si log-in gate.
"""
from datetime import timedelta

import jwt as pyjwt
from django.conf import settings
from django.utils import timezone

JAAS_BASE = 'https://8x8.vc'
TOKEN_TTL = timedelta(hours=2)
CLOCK_SKEW = timedelta(seconds=10)


def is_configured():
    """True when all JaaS secrets are present."""
    return bool(settings.JAAS_ENABLED)


def build_join_url(session, user):
    """Return a JaaS join URL carrying a moderator JWT for `user`."""
    now = timezone.now()
    room = session.room_name
    payload = {
        'aud': 'jitsi',
        'iss': 'chat',
        'sub': settings.JAAS_APP_ID,
        'room': room,
        'nbf': int((now - CLOCK_SKEW).timestamp()),
        'exp': int((now + TOKEN_TTL).timestamp()),
        'context': {
            'user': {
                'id': str(user.id),
                'name': user.full_name,
                'email': user.email,
                'moderator': 'true',
            },
            'features': {
                'recording': 'false',
                'livestreaming': 'false',
                'transcription': 'false',
                'outbound-call': 'false',
            },
        },
    }
    token = pyjwt.encode(
        payload,
        settings.JAAS_PRIVATE_KEY,
        algorithm='RS256',
        headers={'kid': settings.JAAS_KID, 'typ': 'JWT'},
    )
    return f'{JAAS_BASE}/{settings.JAAS_APP_ID}/{room}?jwt={token}'
