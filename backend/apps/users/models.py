"""
User models for the SPT Mentoring Platform.

Supports three primary roles:
  - Scholar  (mentee / young person)
  - Mentor
  - Sponsor  (funder who receives regular updates from Scholars)
  - Admin    (platform staff)
  - Alumni   (graduated Scholars who can peer-mentor)
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class User(AbstractUser):
    class Role(models.TextChoices):
        SCHOLAR = 'scholar', _('Scholar')
        MENTOR = 'mentor', _('Mentor')
        SPONSOR = 'sponsor', _('Sponsor')
        ALUMNI = 'alumni', _('Alumni')
        ADMIN = 'admin', _('Admin')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SCHOLAR)
    email = models.EmailField(unique=True)

    # Profile
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)

    # Engineering/matching
    engineering_discipline = models.CharField(max_length=100, blank=True)
    interests = models.JSONField(default=list, blank=True)

    # Contact preferences
    notification_email = models.BooleanField(default=True)
    notification_sms = models.BooleanField(default=False)

    # Safeguarding
    is_verified = models.BooleanField(default=False, help_text='DBS/safeguarding check complete')
    safeguarding_training_date = models.DateField(null=True, blank=True)

    # CRM reference
    crm_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Soft-delete
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'


class MentorProfile(models.Model):
    """Extended profile for Mentors."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    max_scholars = models.PositiveIntegerField(default=3, help_text='Maximum number of Scholars this Mentor can support')
    specialisms = models.JSONField(default=list, blank=True, help_text='List of engineering specialisms')
    availability = models.TextField(blank=True, help_text='General availability notes')
    linkedin_url = models.URLField(blank=True)
    dbs_check_date = models.DateField(null=True, blank=True)
    dbs_certificate_number = models.CharField(max_length=50, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f'Mentor: {self.user.full_name}'

    @property
    def current_scholar_count(self):
        return self.user.mentor_matches.filter(is_active=True).count()

    @property
    def has_capacity(self):
        return self.current_scholar_count < self.max_scholars


class ScholarProfile(models.Model):
    """Extended profile for Scholars."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='scholar_profile')
    university = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=200, blank=True)
    year_of_study = models.PositiveIntegerField(null=True, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    scholarship_reference = models.CharField(max_length=100, blank=True)
    sponsor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sponsored_scholars', limit_choices_to={'role': User.Role.SPONSOR}
    )
    goals = models.TextField(blank=True, help_text='Scholar goals for the mentoring programme')
    soft_skills_baseline = models.JSONField(default=dict, blank=True)
    soft_skills_current = models.JSONField(default=dict, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f'Scholar: {self.user.full_name}'


class SponsorProfile(models.Model):
    """Extended profile for Sponsors."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sponsor_profile')
    organisation = models.CharField(max_length=200, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    update_frequency_days = models.PositiveIntegerField(
        default=90, help_text='Expected update frequency from Scholars (days)'
    )

    history = HistoricalRecords()

    def __str__(self):
        return f'Sponsor: {self.user.full_name}'


class MentoringMatch(models.Model):
    """Links a Scholar to one or more Mentors."""
    scholar = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='scholar_matches',
        limit_choices_to={'role': User.Role.SCHOLAR}
    )
    mentor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='mentor_matches',
        limit_choices_to={'role': User.Role.MENTOR}
    )
    matched_on = models.DateTimeField(auto_now_add=True)
    matched_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='matches_created'
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ('scholar', 'mentor')
        verbose_name = 'Mentoring Match'

    def __str__(self):
        return f'{self.scholar.full_name} ↔ {self.mentor.full_name}'
