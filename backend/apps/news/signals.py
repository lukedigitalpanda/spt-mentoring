from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender='news.NewsItem')
def _capture_pre_save_status(sender, instance, **kwargs):
    """Store the previous status so post_save can detect the transition."""
    if instance.pk:
        try:
            instance._pre_save_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).get()
        except sender.DoesNotExist:
            instance._pre_save_status = None
    else:
        instance._pre_save_status = None


@receiver(post_save, sender='news.NewsItem')
def _notify_on_publish(sender, instance, created, **kwargs):
    """Create in-app notifications when a news item is first published."""
    from django.utils import timezone
    from apps.notifications.models import Notification
    from apps.users.models import User

    was_published = getattr(instance, '_pre_save_status', None) == 'published'
    if was_published or instance.status != 'published':
        return

    # Set published_at if not already set
    if not instance.published_at:
        sender.objects.filter(pk=instance.pk).update(published_at=timezone.now())

    # Determine target roles from audience_list (or fall back to audience)
    audience = instance.audience_list if instance.audience_list else [instance.audience]
    if 'all' in audience:
        recipients = User.objects.filter(is_active=True, is_staff=False).exclude(role='admin')
    else:
        recipients = User.objects.filter(is_active=True, role__in=audience)

    notifications = [
        Notification(
            user=u,
            notification_type=Notification.Type.NEWS_ITEM,
            title='New article published',
            body=instance.title,
            link=f'/news/{instance.pk}',
        )
        for u in recipients
    ]
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)
