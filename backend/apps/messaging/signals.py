"""
Signals for the messaging app.
Creates in-app notifications when messages are delivered to recipients.
Creates admin notifications when an abuse report is submitted.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='messaging.Message')
def notify_recipients_on_delivered_message(sender, instance, created, **kwargs):
    """Create a Notification for each participant who isn't the sender when a message is delivered."""
    if instance.status != 'delivered':
        return

    from apps.notifications.models import Notification

    other_participants = instance.conversation.participants.exclude(pk=instance.sender_id)
    for user in other_participants:
        Notification.objects.create(
            user=user,
            notification_type=Notification.Type.MESSAGE,
            title=f'New message from {instance.sender.full_name}',
            body=instance.body[:100],
            link='/messages',
        )


@receiver(post_save, sender='messaging.AbuseReport')
def notify_admins_on_abuse_report(sender, instance, created, **kwargs):
    """Notify all admin users immediately when an abuse report is submitted."""
    if not created:
        return

    from apps.users.models import User
    from apps.notifications.models import Notification

    admins = User.objects.filter(role='admin', is_active=True)
    reporter_name = instance.reporter.full_name
    reported_name = instance.reported_user.full_name if instance.reported_user else 'unknown user'

    for admin in admins:
        Notification.objects.create(
            user=admin,
            notification_type=Notification.Type.SYSTEM,
            title='Abuse report submitted',
            body=f'{reporter_name} reported {reported_name}. Review required.',
            link='/messages',
        )
