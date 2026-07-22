"""
Template tag that injects the "Action Required" to-do counts into the
Django admin index page.

Usage in a template:
    {% load admin_todo %}
    {% admin_todo_panel %}
"""
from django import template

register = template.Library()


@register.inclusion_tag('admin/todo_panel.html', takes_context=True)
def admin_todo_panel(context):
    """
    Query all items that need admin attention and return counts + direct links.
    Rendered via admin/todo_panel.html as a panel at the top of the dashboard.
    """
    try:
        from apps.messaging.models import Message, Conversation, AbuseReport
        from apps.forums.models import Post

        # Messages flagged by the moderation pipeline — need approve/reject
        flagged_messages = Message.objects.filter(status='flagged').count()

        # Messages auto-blocked by the moderation pipeline in the last 7 days.
        # These were rejected outright (sender already notified), so they are
        # surfaced for staff visibility/audit, NOT counted as pending actions.
        from django.utils import timezone
        from datetime import timedelta
        blocked_messages = Message.objects.filter(
            status='blocked',
            sent_at__gte=timezone.now() - timedelta(days=7),
        ).count()

        # Forum posts that are either held pending or flagged — need review
        pending_posts = Post.objects.filter(status__in=['pending', 'flagged']).count()

        # Open or under-review abuse/safeguarding reports
        open_reports = AbuseReport.objects.filter(
            status__in=['open', 'under_review']
        ).count()

        # Inbound support conversations — DIRECT conversations where a user
        # contacted Arkwright for help (subject='Support').  Filter to OPEN
        # explicitly (not just exclude RESOLVED) so legacy NULL-status rows
        # created before the support_status field was added don't inflate the count.
        support_convs = (
            Conversation.objects
            .filter(
                participants__email='arkwright@spt.org',
                conversation_type=Conversation.ConversationType.DIRECT,
                subject='Support',
                support_status=Conversation.SupportStatus.OPEN,
            )
            .distinct()
            .count()
        )

        total = flagged_messages + pending_posts + open_reports + support_convs

        return {
            'flagged_messages': flagged_messages,
            'blocked_messages': blocked_messages,
            'pending_posts': pending_posts,
            'open_reports': open_reports,
            'support_convs': support_convs,
            'total_actions': total,
            'has_actions': total > 0,
        }
    except Exception:
        # Never let a tag error break the admin dashboard
        return {
            'flagged_messages': 0,
            'blocked_messages': 0,
            'pending_posts': 0,
            'open_reports': 0,
            'support_convs': 0,
            'total_actions': 0,
            'has_actions': False,
        }
