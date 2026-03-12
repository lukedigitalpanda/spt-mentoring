from rest_framework import serializers
from .models import AvailabilitySlot, MentoringSession, SessionFeedback


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)

    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'mentor', 'mentor_name', 'start_time', 'end_time', 'is_booked', 'notes']
        read_only_fields = ['is_booked']


class SessionFeedbackSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.full_name', read_only=True)

    class Meta:
        model = SessionFeedback
        fields = ['id', 'session', 'from_user', 'from_user_name', 'rating',
                  'highlights', 'improvements', 'would_recommend', 'created_at']
        read_only_fields = ['from_user', 'created_at']


class MentoringSessionSerializer(serializers.ModelSerializer):
    mentor_name  = serializers.CharField(source='mentor.full_name',  read_only=True)
    scholar_name = serializers.CharField(source='scholar.full_name', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    feedback = SessionFeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = MentoringSession
        fields = [
            'id', 'mentor', 'mentor_name', 'scholar', 'scholar_name',
            'slot', 'title', 'start_time', 'end_time', 'status',
            'meeting_url', 'agenda', 'mentor_notes', 'scholar_notes',
            'duration_minutes', 'feedback', 'created_at',
        ]
        read_only_fields = ['meeting_url', 'created_by', 'created_at']
