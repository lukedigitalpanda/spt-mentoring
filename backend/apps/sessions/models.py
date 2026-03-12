"""
Session Booking models for SPT Mentoring Platform.

Covers:
  - AvailabilitySlot  (mentor publishes open time windows)
  - MentoringSession  (a booked/confirmed session)
  - SessionFeedback   (post-session star rating + comments from both parties)
"""
import hashlib
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class AvailabilitySlot(models.Model):
    """A window of time a mentor is available to be booked."""
    mentor = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='availability_slots',
        limit_choices_to={'role': 'mentor'},
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True, help_text='Optional notes for scholars')

    history = HistoricalRecords()

    class Meta:
        ordering = ['start_time']
        verbose_name = 'Availability Slot'

    def __str__(self):
        return f"{self.mentor.full_name}: {self.start_time.strftime('%d %b %Y %H:%M')}"


class MentoringSession(models.Model):
    """A booked mentoring session between a scholar and mentor."""

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Pending confirmation')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')
        COMPLETED = 'completed', _('Completed')
        NO_SHOW   = 'no_show',   _('No show')

    mentor = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='mentor_sessions',
        limit_choices_to={'role': 'mentor'},
    )
    scholar = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='scholar_sessions',
        limit_choices_to={'role__in': ['scholar', 'alumni']},
    )
    slot = models.OneToOneField(
        AvailabilitySlot, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='session',
    )
    title = models.CharField(max_length=200, default='Mentoring Session')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    meeting_url = models.CharField(max_length=500, blank=True)
    agenda = models.TextField(blank=True, help_text='Topics to cover in this session')
    mentor_notes = models.TextField(blank=True)
    scholar_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, related_name='sessions_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Mentoring Session'

    def save(self, *args, **kwargs):
        if not self.meeting_url:
            token = hashlib.md5(
                f"spt-{self.mentor_id}-{self.scholar_id}-{self.start_time}".encode()
            ).hexdigest()[:10]
            self.meeting_url = f"https://meet.jit.si/SPTMentoring-{token}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scholar.full_name} ↔ {self.mentor.full_name} ({self.start_time.strftime('%d %b %Y %H:%M')})"

    @property
    def duration_minutes(self):
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def is_upcoming(self):
        return self.start_time > timezone.now() and self.status == self.Status.CONFIRMED


class SessionFeedback(models.Model):
    """Post-session feedback submitted by either party."""
    session = models.ForeignKey(
        MentoringSession, on_delete=models.CASCADE,
        related_name='feedback',
    )
    from_user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='session_feedback_given',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1 (poor) – 5 (excellent)',
    )
    highlights = models.TextField(blank=True, help_text='What went well?')
    improvements = models.TextField(blank=True, help_text='What could be better?')
    would_recommend = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'from_user')
        verbose_name = 'Session Feedback'

    def __str__(self):
        return f"Feedback by {self.from_user.full_name} – {self.rating}★"
