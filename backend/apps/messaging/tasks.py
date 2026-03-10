"""Celery tasks for async messaging operations."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_mass_message_task(mass_message_id):
    """Send a MassMessage to all targeted recipients via email."""
    from django.core.mail import send_mail
    from django.utils import timezone
    from apps.users.models import User
    from .models import MassMessage

    try:
        msg = MassMessage.objects.get(pk=mass_message_id)
    except MassMessage.DoesNotExist:
        logger.error('MassMessage %d not found', mass_message_id)
        return

    # Collect recipients
    qs = User.objects.filter(is_active=True, notification_email=True)
    if msg.recipient_roles:
        qs = qs.filter(role__in=msg.recipient_roles)
    if msg.recipient_cohorts.exists():
        cohort_ids = msg.recipient_cohorts.values_list('pk', flat=True)
        qs = qs.filter(cohort_memberships__cohort_id__in=cohort_ids).distinct()

    emails = list(qs.values_list('email', flat=True))
    if not emails:
        logger.warning('MassMessage %d has no recipients', mass_message_id)
        return

    for email in emails:
        try:
            send_mail(
                subject=msg.subject,
                message=msg.body,
                from_email=msg.send_from_email,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Failed to send mass message to %s', email)

    msg.status = MassMessage.Status.SENT
    msg.sent_at = timezone.now()
    msg.recipient_count = len(emails)
    msg.save(update_fields=['status', 'sent_at', 'recipient_count'])
    logger.info('MassMessage %d sent to %d recipients', mass_message_id, len(emails))


@shared_task
def send_no_contact_reminders():
    """
    Send reminders when Scholar/Mentor pairs haven't messaged each other
    within the configured period.
    """
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone
    from datetime import timedelta
    from apps.users.models import MentoringMatch, User
    from apps.messaging.models import Message

    threshold = timezone.now() - timedelta(days=settings.NO_CONTACT_REMINDER_DAYS)

    for match in MentoringMatch.objects.filter(is_active=True).select_related('scholar', 'mentor'):
        # Check last message between this pair
        participants_ids = [match.scholar_id, match.mentor_id]
        last_msg = Message.objects.filter(
            conversation__participants__in=participants_ids,
            status=Message.Status.DELIVERED,
        ).order_by('-sent_at').first()

        if last_msg is None or last_msg.sent_at < threshold:
            for user in [match.scholar, match.mentor]:
                if user.notification_email:
                    send_mail(
                        subject='SPT Mentoring – Time to connect!',
                        message=(
                            f'Hi {user.first_name},\n\n'
                            'It looks like you and your mentoring partner haven\'t been in touch recently. '
                            'Please log in to the SPT Mentoring Platform and send a message.\n\n'
                            'Best regards,\nSPT Mentoring Team'
                        ),
                        from_email=settings.MENTORING_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )


@shared_task
def send_sponsor_update_reminders():
    """Remind scholars to send updates to their sponsors."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone
    from datetime import timedelta
    from apps.users.models import User
    from apps.messaging.models import Message

    scholars = User.objects.filter(role=User.Role.SCHOLAR, is_active=True).select_related('scholar_profile__sponsor')

    for scholar in scholars:
        profile = getattr(scholar, 'scholar_profile', None)
        if not profile or not profile.sponsor:
            continue
        sponsor_profile = getattr(profile.sponsor, 'sponsor_profile', None)
        freq = getattr(sponsor_profile, 'update_frequency_days', 90)
        threshold = timezone.now() - timedelta(days=freq)

        last_update = Message.objects.filter(
            conversation__conversation_type='sponsor_update',
            sender=scholar,
            status=Message.Status.DELIVERED,
        ).order_by('-sent_at').first()

        if last_update is None or last_update.sent_at < threshold:
            if scholar.notification_email:
                send_mail(
                    subject='SPT Scholarships – Time to update your sponsor',
                    message=(
                        f'Hi {scholar.first_name},\n\n'
                        f'Your sponsor {profile.sponsor.full_name} is due an update from you. '
                        'Please log in to the platform and send them an update on your progress.\n\n'
                        'Best regards,\nSPT Scholarships Team'
                    ),
                    from_email=settings.SCHOLARSHIPS_FROM_EMAIL,
                    recipient_list=[scholar.email],
                    fail_silently=True,
                )
