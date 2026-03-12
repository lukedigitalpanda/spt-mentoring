from django.contrib import admin
from .models import AvailabilitySlot, MentoringSession, SessionFeedback


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['mentor', 'start_time', 'end_time', 'is_booked']
    list_filter = ['is_booked', 'mentor']
    ordering = ['start_time']


@admin.register(MentoringSession)
class MentoringSessionAdmin(admin.ModelAdmin):
    list_display = ['scholar', 'mentor', 'start_time', 'status', 'duration_minutes']
    list_filter = ['status']
    search_fields = ['scholar__first_name', 'mentor__first_name', 'title']
    ordering = ['-start_time']


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['session', 'from_user', 'rating', 'created_at']
    list_filter = ['rating']
