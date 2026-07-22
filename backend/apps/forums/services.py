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
    """
    if post.status != Post.Status.VISIBLE:
        return

    # Atomically claim the notification for this post.  If another save already
    # claimed it (or is racing us), do nothing.
    claimed = Post.objects.filter(pk=post.pk, mentor_notified=False).update(mentor_notified=True)
    if not claimed:
        return
    # Keep the in-memory instance consistent with the DB so a later full save()
    # of this same instance cannot reset the flag and re-notify.
    post.mentor_notified = True

    author = post.author
    if author.role != User.Role.SCHOLAR:
        return

    forum = post.thread.forum
    mentors = User.objects.filter(
        mentor_matches__scholar=author,
        mentor_matches__is_active=True,
        is_active=True,
    ).distinct()

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

        try:
            from apps.notifications.digest import queue_notification_email
            queue_notification_email(notification)
        except Exception:
            # Email queueing must never break post creation / in-app / push.
            logger.exception(
                'Failed to queue forum-post notification email for notification %s',
                notification.pk,
            )
