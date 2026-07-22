"""
Signals for the forums app.

Notifies a scholar's matched mentor(s) when their forum post becomes visible
(on clean creation or on moderation approval), and notifies earlier thread
participants of the same reply - see services.py for the rules.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='forums.Post')
def notify_mentors_on_visible_post(sender, instance, created, **kwargs):
    from .services import notify_mentors_of_scholar_post, notify_thread_participants_of_reply
    already_notified = notify_mentors_of_scholar_post(instance)
    notify_thread_participants_of_reply(instance, skip_user_ids=already_notified)
