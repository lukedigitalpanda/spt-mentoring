"""
Survey functionality – create and distribute surveys to users.
Results feed into reports and can link to goals/soft-skill tracking.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Survey(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        ACTIVE = 'active', _('Active')
        CLOSED = 'closed', _('Closed')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    programme = models.ForeignKey(
        'cohorts.Programme', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='surveys'
    )
    cohort = models.ForeignKey(
        'cohorts.Cohort', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='surveys'
    )
    target_roles = models.JSONField(default=list, blank=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Customer Voice integration reference
    customer_voice_id = models.CharField(max_length=100, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.title


class Question(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = 'text', _('Free text')
        RATING = 'rating', _('Rating (1-5)')
        MULTIPLE_CHOICE = 'multiple_choice', _('Multiple choice')
        CHECKBOX = 'checkbox', _('Checkbox (multi-select)')
        SCALE = 'scale', _('Scale')

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)
    options = models.JSONField(default=list, blank=True, help_text='For multiple_choice/checkbox')
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    # Maps to a soft-skill dimension for progress tracking
    soft_skill_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Q{self.order}: {self.text[:60]}'


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    respondent = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='survey_responses')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('survey', 'respondent')

    def __str__(self):
        return f'{self.respondent.full_name} → {self.survey.title}'


class Answer(models.Model):
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value = models.TextField()

    def __str__(self):
        return f'Answer to Q{self.question.order}'
