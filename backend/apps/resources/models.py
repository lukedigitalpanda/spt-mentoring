"""
Resource bank – documents, links, and websites shared with users.
Supports document sharing between users.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class ResourceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Resource Categories'

    def __str__(self):
        return self.name


class Resource(models.Model):
    class ResourceType(models.TextChoices):
        DOCUMENT = 'document', _('Document')
        LINK = 'link', _('Link / Website')
        VIDEO = 'video', _('Video')

    class Audience(models.TextChoices):
        ALL = 'all', _('All Users')
        SCHOLAR = 'scholar', _('Scholars')
        MENTOR = 'mentor', _('Mentors')
        SPONSOR = 'sponsor', _('Sponsors')
        ADMIN = 'admin', _('Admin only')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    category = models.ForeignKey(ResourceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='resources')
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    url = models.URLField(blank=True)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    programme = models.ForeignKey(
        'cohorts.Programme', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resources'
    )
    uploaded_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='resources_uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SharedDocument(models.Model):
    """Document shared between two specific users (mentor <-> scholar)."""
    file = models.FileField(upload_to='shared_documents/')
    filename = models.CharField(max_length=255)
    shared_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='documents_shared')
    shared_with = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='documents_received')
    shared_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)
    is_deleted_by_sender = models.BooleanField(default=False)
    is_deleted_by_recipient = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.filename} ({self.shared_by.full_name} → {self.shared_with.full_name})'
