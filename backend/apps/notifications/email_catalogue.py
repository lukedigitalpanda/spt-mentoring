"""Single source of truth for the emails the platform sends (read-only catalogue)."""
from dataclasses import dataclass, field

from apps.messaging.tasks import NO_CONTACT_REMINDER_SUBJECT, SPONSOR_UPDATE_SUBJECT
from apps.users.auth_views import PASSWORD_RESET_SUBJECT


@dataclass(frozen=True)
class EmailSpec:
    key: str
    name: str
    trigger: str
    recipients: str
    subject: str
    body: str
    debounced: bool = False
    source: str = ''
    notes: str = ''


EMAIL_CATALOGUE = [
    EmailSpec(
        key='message', name='New message',
        trigger='Another user sends you a direct/group message',
        recipients='Message recipient(s)',
        subject='New message from {sender name}',
        body='{message excerpt}\n\n{link to /messages}',
        debounced=True, source='apps/messaging/signals.py + apps/notifications/emails.py',
        notes='If 2+ notifications are pending in the debounce window they are combined into a notification_digest instead.',
    ),
    EmailSpec(
        key='scholar_forum_post', name='Scholar forum post',
        trigger='Your matched scholar posts in a forum you can see',
        recipients='Matched mentor(s) of the posting scholar',
        subject='{scholar name} posted in the forum',
        body='{thread title}: {post excerpt}\n\n{link to /forums}',
        debounced=True, source='apps/forums/services.py',
    ),
    EmailSpec(
        key='notification_digest', name='Notification digest',
        trigger='Debounce window closes with 2+ unread pending notifications',
        recipients='The recipient of the batched notifications',
        subject='You have {N} new notifications on SPT Mentoring',
        body='Hi {first name},\n\nYou have {counts} on SPT Mentoring:\n\n- {title}\n  {link}\n...\n\nLog in to the SPT Mentoring Platform to read them.',
        source='apps/notifications/digest.py',
    ),
    EmailSpec(
        key='mass_message', name='Mass message',
        trigger='Admin sends a broadcast from the Mass Message admin',
        recipients='All users matching the broadcast filters',
        subject='{admin-authored subject}',
        body='{admin-authored body}',
        source='apps/messaging/tasks.py:send_mass_message_task',
        notes='Subject/body are authored by the admin per broadcast; from-address is the broadcast sender.',
    ),
    EmailSpec(
        key='no_contact_reminder', name='No-contact reminder',
        trigger='A scholar/mentor pair has not messaged for NO_CONTACT_REMINDER_DAYS (Beat, daily 9am)',
        recipients='Both members of the pair (if email on)',
        subject=NO_CONTACT_REMINDER_SUBJECT,
        body="Hi {first name},\n\nIt looks like you and your mentoring partner haven't been in touch recently. Please log in to the SPT Mentoring Platform and send a message.\n\nBest regards,\nSPT Mentoring Team",
        source='apps/messaging/tasks.py:send_no_contact_reminders',
    ),
    EmailSpec(
        key='sponsor_update_reminder', name='Sponsor update reminder',
        trigger='A scholar is overdue to update their sponsor (Beat, Monday 9:30am)',
        recipients='The scholar (if email on)',
        subject=SPONSOR_UPDATE_SUBJECT,
        body='Hi {first name},\n\nYour sponsor {sponsor name} is due an update from you. Please log in to the platform and send them an update on your progress.\n\nBest regards,\nSPT Scholarships Team',
        source='apps/messaging/tasks.py:send_sponsor_update_reminders',
    ),
    EmailSpec(
        key='moderation_alert', name='Moderation alert',
        trigger='A message or forum post is flagged for review',
        recipients='All active staff/admin users',
        subject='[SPT Moderation] Flagged message requires review (#{id})',
        body='A message has been flagged for review.\n\nSender:       {name} ({email})\nTriggered by: "{term}"\nPreview:      {first 200 chars of message}\nReview it here: {admin url}',
        source='apps/moderation/service.py:_alert_staff',
    ),
    EmailSpec(
        key='password_reset', name='Password reset',
        trigger='A user requests a password reset',
        recipients='The requesting user',
        subject=PASSWORD_RESET_SUBJECT,
        body='Hi {first name},\n\nYou requested a password reset for your Arkwright Mentoring account.\n\nClick the link below to choose a new password:\n\n{reset url}\n\nThis link is valid for 3 days. If you did not request this, you can safely ignore this email.\n\nThe Arkwright Mentoring team',
        source='apps/users/auth_views.py:PasswordResetRequestView',
    ),
]


# (subject substring, catalogue key) — first match wins. Order matters.
_CATEGORY_MATCHERS = [
    ('[SPT Moderation] Flagged message', 'moderation_alert'),
    ('Reset your password', 'password_reset'),
    ('new notifications on SPT Mentoring', 'notification_digest'),
    ('New message from', 'message'),
    ('posted in the forum', 'scholar_forum_post'),
    (NO_CONTACT_REMINDER_SUBJECT, 'no_contact_reminder'),
    (SPONSOR_UPDATE_SUBJECT, 'sponsor_update_reminder'),
]


def infer_category(subject):
    """Best-effort classify a sent email's subject to a catalogue key ('' if unknown)."""
    subject = subject or ''
    for needle, key in _CATEGORY_MATCHERS:
        if needle in subject:
            return key
    return ''
