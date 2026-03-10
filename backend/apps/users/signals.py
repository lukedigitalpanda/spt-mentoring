"""Auto-create role-specific profiles when a User is created."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, MentorProfile, ScholarProfile, SponsorProfile


@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.role == User.Role.MENTOR:
        MentorProfile.objects.get_or_create(user=instance)
    elif instance.role in (User.Role.SCHOLAR, User.Role.ALUMNI):
        ScholarProfile.objects.get_or_create(user=instance)
    elif instance.role == User.Role.SPONSOR:
        SponsorProfile.objects.get_or_create(user=instance)
