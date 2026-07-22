"""Auto-create role-specific profiles when a User is created or updated."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, MentorProfile, ScholarProfile, SponsorProfile, MentoringMatch


def _ensure_profiles_for_roles(instance):
    """ISS-H: Create any missing role profiles for the given user's primary + secondary roles."""
    all_roles = instance.all_roles
    if User.Role.MENTOR in all_roles or User.Role.ALUMNI in all_roles:
        MentorProfile.objects.get_or_create(user=instance)
    if User.Role.SCHOLAR in all_roles or User.Role.ALUMNI in all_roles:
        ScholarProfile.objects.get_or_create(user=instance)
    if User.Role.SPONSOR in all_roles:
        SponsorProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    # Run on creation (all roles) and on update (to handle secondary_roles changes).
    # Use update_fields guard to avoid recursion when saving only non-role fields.
    update_fields = kwargs.get('update_fields')
    if update_fields and 'role' not in update_fields and 'secondary_roles' not in update_fields:
        return
    _ensure_profiles_for_roles(instance)


def _find_match_conversation(scholar, mentor):
    """Return the DIRECT conversation shared by this scholar-mentor pair, or None.

    Searches first by live participant membership, then falls back to matching
    by subject so it still works after participants were removed on deactivation.
    """
    from apps.messaging.models import Conversation
    # Primary search: both are still active participants
    conv = (
        Conversation.objects
        .filter(conversation_type=Conversation.ConversationType.DIRECT, participants=scholar)
        .filter(participants=mentor)
        .first()
    )
    if conv:
        return conv
    # Fallback: one or both were removed on deactivation — locate by subject
    expected_subject = f'{scholar.full_name} & {mentor.full_name}'
    return (
        Conversation.objects
        .filter(
            conversation_type=Conversation.ConversationType.DIRECT,
            subject=expected_subject,
        )
        .first()
    )


@receiver(post_save, sender=MentoringMatch)
def ensure_match_conversation(sender, instance, created, **kwargs):
    """Manage the direct conversation for a mentor-scholar match.

    Active match (new or reinstated)
    ─────────────────────────────────
    • Re-activates either user if they were deactivated.
    • Ensures a DIRECT conversation exists and both are participants.
    • Notifies both parties via in-app Notification.

    Deactivated match
    ─────────────────
    • Removes both parties from the conversation so stale threads no
      longer appear in their sidebar.  The conversation record and its
      messages are preserved for audit; they will be restored on
      reinstatement.
    """
    from apps.messaging.models import Conversation

    if not instance.is_active:
        # Match deactivated: leave participants in the conversation so both
        # parties can still read historic messages.  New messages are blocked
        # at the API level by checking match status on send.
        return

    # ── Active match ──────────────────────────────────────────────────────────

    # Re-activate users if either was deactivated (e.g. as part of pausing the match)
    for user in (instance.scholar, instance.mentor):
        if not user.is_active:
            user.is_active = True
            user.deactivated_at = None
            user.save(update_fields=['is_active', 'deactivated_at'])

    # Ensure a direct conversation channel exists between the pair.
    # If one already exists, re-add both as participants in case they were
    # removed (e.g. during a match pause) so messaging is always restored.
    existing = _find_match_conversation(instance.scholar, instance.mentor)
    if existing:
        existing.participants.add(instance.scholar, instance.mentor)
    else:
        conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT,
            subject=f'{instance.scholar.full_name} & {instance.mentor.full_name}',
        )
        conv.participants.add(instance.scholar, instance.mentor)

    # ── Notifications ─────────────────────────────────────────────────────────
    from apps.notifications.models import Notification

    if created:
        # Fresh match creation — inform both parties they've been linked.
        Notification.objects.create(
            user=instance.scholar,
            notification_type=Notification.Type.MATCH,
            title='You have a new mentor!',
            body=f'You have been matched with {instance.mentor.full_name}. Head to Messages to say hello.',
            link='/messages',
        )
        Notification.objects.create(
            user=instance.mentor,
            notification_type=Notification.Type.MATCH,
            title='New scholar matched',
            body=f'{instance.scholar.full_name} has been matched with you. Head to Messages to introduce yourself.',
            link='/messages',
        )
    else:
        # Reinstatement — let both parties know messaging is back.
        Notification.objects.create(
            user=instance.scholar,
            notification_type=Notification.Type.MATCH,
            title='Your mentoring match has been reinstated',
            body=(
                f'Your match with {instance.mentor.full_name} has been restored. '
                'You can now send and receive messages again.'
            ),
            link='/messages',
        )
        Notification.objects.create(
            user=instance.mentor,
            notification_type=Notification.Type.MATCH,
            title='Mentoring match reinstated',
            body=(
                f'Your match with {instance.scholar.full_name} has been restored. '
                'You can now send and receive messages again.'
            ),
            link='/messages',
        )

    # ── Email ─────────────────────────────────────────────────────────────────
    # Fires for both the fresh-match and reinstatement branches above; skipped
    # entirely on deactivation because we returned early when not is_active.
    from apps.messaging.tasks import send_match_notification_emails
    send_match_notification_emails.delay(instance.id)
