"""
News items and home page promotional content.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class NewsItem(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')
        ARCHIVED = 'archived', _('Archived')

    class Audience(models.TextChoices):
        ALL = 'all', _('All Users')
        SCHOLAR = 'scholar', _('Scholars')
        MENTOR = 'mentor', _('Mentors')
        SPONSOR = 'sponsor', _('Sponsors')

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(upload_to='news/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    is_featured = models.BooleanField(default=False, help_text='Show on home page as featured item')
    programme = models.ForeignKey(
        'cohorts.Programme', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='news_items'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='news_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title


class PromotionalBanner(models.Model):
    """Home page hero/promotional banners."""
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    programme = models.ForeignKey(
        'cohorts.Programme', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title
