"""
Goals & Milestones for SPT Mentoring Platform.

Scholars (and mentors) can define structured goals with trackable
milestones, categories, and due dates.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Goal(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'active',    _('Active')
        COMPLETED = 'completed', _('Completed')
        PAUSED    = 'paused',    _('Paused')

    class Category(models.TextChoices):
        CAREER      = 'career',      _('Career')
        TECHNICAL   = 'technical',   _('Technical Skills')
        PERSONAL    = 'personal',    _('Personal Development')
        ACADEMIC    = 'academic',    _('Academic')
        NETWORKING  = 'networking',  _('Networking')
        OTHER       = 'other',       _('Other')

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='goals',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Goal'

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != self.Status.COMPLETED:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name}: {self.title}"

    @property
    def milestone_count(self):
        return self.milestones.count()

    @property
    def completed_milestone_count(self):
        return self.milestones.filter(is_completed=True).count()

    @property
    def progress_percent(self):
        total = self.milestone_count
        if total == 0:
            return 100 if self.status == self.Status.COMPLETED else 0
        return round((self.completed_milestone_count / total) * 100)


class GoalMilestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['due_date', 'id']
        verbose_name = 'Goal Milestone'

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.is_completed:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.goal.title} › {self.title}"
