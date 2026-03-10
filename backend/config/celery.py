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
}
