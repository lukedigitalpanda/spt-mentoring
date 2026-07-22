"""Celery tasks for async messaging operations."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

NO_CONTACT_REMINDER_SUBJECT = 'SPT Mentoring – Time to connect!'
SPONSOR_UPDATE_SUBJECT = 'SPT Scholarships – Time to update your sponsor'
MATCH_EMAIL_SUBJECT = 'SPT Mentoring - You have been matched'


def build_no_contact_body(first_name):
    return (
        f'Hi {first_name},\n\n'
        'It looks like you and your mentoring partner haven\'t been in touch recently. '
        'Please log in to the SPT Mentoring Platform and send a message.\n\n'
        'Best regards,\nSPT Mentoring Team'
    )


def build_sponsor_update_body(first_name, sponsor_name):
    return (
        f'Hi {first_name},\n\n'
        f'Your sponsor {sponsor_name} is due an update from you. '
        'Please log in to the platform and send them an update on your progress.\n\n'
        'Best regards,\nSPT Scholarships Team'
    )


def build_match_email_body(first_name, other_full_name, other_role, link):
    return (
        f'Hi {first_name},\n\n'
        f'You have been matched with your {other_role}, {other_full_name}, '
        'on the SPT Arkwright Mentoring Platform.\n\n'
        f'Send them a message to introduce yourself: {link}\n\n'
        'Best regards,\nSPT Mentoring Team'
    )


@shared_task
def send_mass_message_task(mass_message_id):
    """Send a MassMessage: creates an in-app conversation per recipient + optional email."""
    from django.core.mail import send_mail
    from django.utils import timezone
    from apps.users.models import User
    from apps.notifications.models import Notification
    from .models import MassMessage, Conversation, Message

    try:
        msg = MassMessage.objects.get(pk=mass_message_id)
    except MassMessage.DoesNotExist:
        logger.error('MassMessage %d not found', mass_message_id)
        return

    # Get or create the Arkwright system sender
    arkwright, created = User.objects.get_or_create(
        email='arkwright@spt.org',
        defaults={
            'username': 'arkwright',
            'first_name': 'Arkwright',
            'last_name': '',
            'role': 'admin',
            'is_active': True,
            'notification_email': False,
            'is_verified': True,
        },
    )
    if created:
        arkwright.set_unusable_password()
        arkwright.save()

    # Collect recipients.
    # ISS-H: include users where the target role is primary OR secondary.
    from django.db.models import Q
    qs = User.objects.filter(is_active=True).exclude(pk=arkwright.pk)
    if msg.recipient_roles:
        role_q = Q(role__in=msg.recipient_roles)
        for r in msg.recipient_roles:
            role_q |= Q(secondary_roles__contains=r)
        qs = qs.filter(role_q)
    if msg.recipient_programmes.exists():
        prog_ids = msg.recipient_programmes.values_list('pk', flat=True)
        qs = qs.filter(cohort_memberships__cohort__programme_id__in=prog_ids).distinct()
    if msg.recipient_cohorts.exists():
        cohort_ids = msg.recipient_cohorts.values_list('pk', flat=True)
        qs = qs.filter(cohort_memberships__cohort_id__in=cohort_ids).distinct()

    recipients = list(qs)
    if not recipients:
        logger.warning('MassMessage %d has no recipients', mass_message_id)
        msg.status = MassMessage.Status.SENT
        msg.sent_at = timezone.now()
        msg.recipient_count = 0
        msg.save(update_fields=['status', 'sent_at', 'recipient_count'])
        return

    for recipient in recipients:
        # Create a private 1-to-1 conversation between Arkwright and the recipient.
        # replies_enabled is propagated from the MassMessage so that broadcast-only
        # messages can disable the reply UI for the recipient.
        conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.MASS_MESSAGE,
            subject=msg.subject,
            replies_enabled=msg.replies_enabled,
        )
        conv.participants.add(arkwright, recipient)

        # Insert message already marked DELIVERED (bypasses moderation — it's admin-sent)
        Message.objects.create(
            conversation=conv,
            sender=arkwright,
            body=msg.body,
            status=Message.Status.DELIVERED,
        )

        # In-app notification
        try:
            Notification.objects.create(
                user=recipient,
                notification_type=Notification.Type.MESSAGE,
                title='New message from Arkwright',
                body=msg.subject,
                link='/messages',
            )
        except Exception:
            logger.exception('Failed to create notification for user %d', recipient.pk)

        # Email (only if user has email notifications enabled)
        if recipient.notification_email and recipient.email:
            try:
                send_mail(
                    subject=msg.subject,
                    message=msg.body,
                    from_email=msg.send_from_email,
                    recipient_list=[recipient.email],
                    fail_silently=True,
                )
            except Exception:
                logger.exception('Failed to send email to %s', recipient.email)

    msg.status = MassMessage.Status.SENT
    msg.sent_at = timezone.now()
    msg.recipient_count = len(recipients)
    msg.save(update_fields=['status', 'sent_at', 'recipient_count'])
    logger.info('MassMessage %d sent to %d recipients', mass_message_id, len(recipients))


@shared_task
def send_match_notification_emails(match_id):
    """Email both parties of a newly created or reinstated mentoring match.

    Names the other party by role (mentor/scholar) and links to /messages.
    Respects each recipient's notification_email preference; a missing/
    deactivated match is a silent no-op (it may have been deleted or
    deactivated again by the time the task runs).
    """
    from django.conf import settings
    from django.core.mail import send_mail
    from apps.users.models import MentoringMatch

    match = MentoringMatch.objects.select_related('mentor', 'scholar').filter(id=match_id).first()
    if match is None or not match.is_active:
        return

    link = f'{settings.FRONTEND_URL}/messages'
    pairs = [
        (match.scholar, match.mentor, 'mentor'),
        (match.mentor, match.scholar, 'scholar'),
    ]
    for recipient, other, other_role in pairs:
        if not (recipient.notification_email and recipient.email):
            continue
        send_mail(
            MATCH_EMAIL_SUBJECT,
            build_match_email_body(recipient.first_name, other.full_name, other_role, link),
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email],
            fail_silently=True,
        )


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
                        subject=NO_CONTACT_REMINDER_SUBJECT,
                        message=build_no_contact_body(user.first_name),
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
                    subject=SPONSOR_UPDATE_SUBJECT,
                    message=build_sponsor_update_body(scholar.first_name, profile.sponsor.full_name),
                    from_email=settings.SCHOLARSHIPS_FROM_EMAIL,
                    recipient_list=[scholar.email],
                    fail_silently=True,
                )
