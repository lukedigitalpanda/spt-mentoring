import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('spt_mentoring')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    'no-contact-reminders-daily': {
        'task': 'apps.messaging.tasks.send_no_contact_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9am
    },
    'sponsor-update-reminders-weekly': {
        'task': 'apps.messaging.tasks.send_sponsor_update_reminders',
        'schedule': crontab(hour=9, minute=30, day_of_week=1),  # Monday 9:30am
    },
    'flush-notification-email-digests': {
        'task': 'apps.notifications.tasks.flush_notification_email_digests_task',
        'schedule': 60.0,  # every minute — sends debounced email batches that are due
    },
    'purge-email-logs-daily': {
        'task': 'apps.notifications.tasks.purge_email_logs_task',
        'schedule': crontab(hour=3, minute=15),  # daily 03:15
    },
}
