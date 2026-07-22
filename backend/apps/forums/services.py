"""
N-2: notify a scholar's matched mentor(s) when the scholar's forum post
becomes visible.

Rules (see sprint spec):
  * Only the mentor(s) actively matched to the posting scholar are notified.
  * Only when the post is VISIBLE — held (flagged/pending) and rejected
    (hidden) posts never notify; approval flips the post to visible and this
    runs then.
  * Only mentors who can actually see the forum (visibility scoping) — never
    leak the existence of a post a mentor cannot access.
  * Fires exactly once per post (atomic claim on Post.mentor_notified), so
    edits and re-approvals do not re-notify.

P2-3b: notify earlier thread participants when a reply becomes visible.

Rules:
  * Recipients are the thread creator plus authors of earlier VISIBLE posts
    in the thread, minus the new post's author.
  * Only when the post is VISIBLE (same gating as above).
  * Only participants who can actually see the forum (visibility scoping).
  * Fires exactly once per post (atomic claim on Post.participants_notified).
  * A recipient who already received a SCHOLAR_FORUM_POST notification for
    this same post (via notify_mentors_of_scholar_post above) is not also
    sent a FORUM_REPLY notification for it.
"""
import logging

from apps.users.models import User
from apps.notifications.models import Notification
from .models import Forum, Post

logger = logging.getLogger(__name__)


def notify_mentors_of_scholar_post(post):
    """Notify the posting scholar's matched, forum-visible mentor(s).

    Safe to call for any Post save; it no-ops unless the post is newly visible
    and authored by a scholar.

    Returns the set of user ids that were sent a SCHOLAR_FORUM_POST
    notification for this post (used by notify_thread_participants_of_reply
    to avoid double-notifying the same user for the same post).
    """
    if post.status != Post.Status.VISIBLE:
        return set()

    # Atomically claim the notification for this post.  If another save already
    # claimed it (or is racing us), do nothing.
    claimed = Post.objects.filter(pk=post.pk, mentor_notified=False).update(mentor_notified=True)
    if not claimed:
        return set()
    # Keep the in-memory instance consistent with the DB so a later full save()
    # of this same instance cannot reset the flag and re-notify.
    post.mentor_notified = True

    author = post.author
    if author.role != User.Role.SCHOLAR:
        return set()

    forum = post.thread.forum
    mentors = User.objects.filter(
        mentor_matches__scholar=author,
        mentor_matches__is_active=True,
        is_active=True,
    ).distinct()

    notified_user_ids = set()
    for mentor in mentors:
        # Respect forum visibility — do not reveal posts a mentor cannot access.
        if not Forum.objects.filter(pk=forum.pk).visible_to(mentor).exists():
            continue

        notification = Notification.objects.create(
            user=mentor,
            notification_type=Notification.Type.SCHOLAR_FORUM_POST,
            title=f'{author.full_name} posted in the forum',
            body=f'{post.thread.title}: {post.body[:100]}',
            link=f'/forums?thread={post.thread_id}',
        )
        notified_user_ids.add(mentor.pk)

        try:
            from apps.notifications.digest import queue_notification_email
            queue_notification_email(notification)
        except Exception:
            # Email queueing must never break post creation / in-app / push.
            logger.exception(
                'Failed to queue forum-post notification email for notification %s',
                notification.pk,
            )

    return notified_user_ids


def notify_thread_participants_of_reply(post, skip_user_ids=None):
    """Notify earlier participants of ``post``'s thread that a reply is visible.

    Recipients are the thread creator plus the authors of earlier VISIBLE
    posts in the thread, minus the new post's author, minus anyone in
    ``skip_user_ids`` (used to avoid double-notifying a matched mentor who
    already got a SCHOLAR_FORUM_POST notification for this same post).

    Safe to call for any Post save; it no-ops unless the post is newly visible.
    """
    if post.status != Post.Status.VISIBLE:
        return set()

    # Atomically claim the notification for this post.  If another save already
    # claimed it (or is racing us), do nothing.
    claimed = Post.objects.filter(pk=post.pk, participants_notified=False).update(
        participants_notified=True
    )
    if not claimed:
        return set()
    # Keep the in-memory instance consistent with the DB so a later full save()
    # of this same instance cannot reset the flag and re-notify.
    post.participants_notified = True

    thread = post.thread
    skip_user_ids = skip_user_ids or set()

    author_ids = set(
        thread.posts.filter(status=Post.Status.VISIBLE)
        .exclude(author=post.author)
        .values_list('author_id', flat=True)
    )
    author_ids.add(thread.created_by_id)
    author_ids.discard(post.author_id)
    author_ids -= set(skip_user_ids)

    if not author_ids:
        return set()

    forum = thread.forum
    participants = User.objects.filter(pk__in=author_ids, is_active=True)

    notified_user_ids = set()
    for participant in participants:
        # Respect forum visibility - do not reveal posts a user cannot access.
        if not Forum.objects.filter(pk=forum.pk).visible_to(participant).exists():
            continue

        notification = Notification.objects.create(
            user=participant,
            notification_type=Notification.Type.FORUM_REPLY,
            title=f'New reply in "{thread.title}"',
            body=post.body[:100],
            link=f'/forums?thread={thread.id}',
        )
        notified_user_ids.add(participant.pk)

        try:
            from apps.notifications.digest import queue_notification_email
            queue_notification_email(notification)
        except Exception:
            # Email queueing must never break post creation / in-app / push.
            logger.exception(
                'Failed to queue forum-reply notification email for notification %s',
                notification.pk,
            )

    return notified_user_ids
