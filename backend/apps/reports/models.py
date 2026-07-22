from django.db import models


class MentoringReport(models.Model):
    """Proxy/unmanaged model used solely to register the Mentoring Contact Report admin page."""
    class Meta:
        managed = False
        verbose_name = 'Mentoring Report'
        verbose_name_plural = 'Mentoring Reports'
        app_label = 'reports'
