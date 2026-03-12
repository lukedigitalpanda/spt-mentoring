"""
Send a browser push notification whenever a Notification object is created.
Fires as a post_save signal so it works regardless of how the Notification is created.
"""
import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


@receiver(post_save, sender='notifications.Notification')
def send_push_on_notification(sender, instance, created, **kwargs):
    if not created:
        return

    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_public = getattr(settings, 'VAPID_PUBLIC_KEY', '')
    vapid_email = getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@spt.org')

    if not vapid_private or not vapid_public:
        return  # VAPID not configured — skip silently

    try:
        from pywebpush import webpush, WebPushException
        from .models import PushSubscription

        subscriptions = PushSubscription.objects.filter(user=instance.user)
        payload = json.dumps({
            'title': instance.title,
            'body': instance.body,
            'link': instance.link,
            'type': instance.notification_type,
        })

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                    },
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={
                        'sub': f'mailto:{vapid_email}',
                    },
                )
            except WebPushException as exc:
                if exc.response and exc.response.status_code in (404, 410):
                    # Subscription expired — clean up
                    sub.delete()
                else:
                    logger.warning("Push send failed for %s: %s", sub.endpoint[:60], exc)
    except Exception:
        logger.exception("Unexpected error sending push notifications")
