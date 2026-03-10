"""
Cohort management – groups Scholars/Mentors by programme year.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Programme(models.Model):
    """A named mentoring programme (e.g. 'Engineering Scholars 2024')."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    branding_colour = models.CharField(max_length=7, default='#003087', help_text='Hex colour code')
    branding_logo = models.ImageField(upload_to='branding/', blank=True, null=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Cohort(models.Model):
    """A cohort within a programme – typically one academic year."""
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='cohorts')
    name = models.CharField(max_length=200)
    year = models.PositiveIntegerField(help_text='Academic year start (e.g. 2024)')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('programme', 'year')
        ordering = ['-year']

    def __str__(self):
        return f'{self.programme.name} – {self.name}'


class CohortMembership(models.Model):
    """Associates a user with a cohort and tracks their role within it."""
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='cohort_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('cohort', 'user')

    def __str__(self):
        return f'{self.user.full_name} in {self.cohort}'
