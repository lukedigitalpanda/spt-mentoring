from rest_framework import serializers
from .models import Goal, GoalMilestone


class GoalMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalMilestone
        fields = ['id', 'goal', 'title', 'is_completed', 'completed_at', 'due_date']
        read_only_fields = ['completed_at']


class GoalSerializer(serializers.ModelSerializer):
    milestones = GoalMilestoneSerializer(many=True, read_only=True)
    milestone_count = serializers.IntegerField(read_only=True)
    completed_milestone_count = serializers.IntegerField(read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'user', 'title', 'description', 'category', 'status',
            'due_date', 'created_at', 'completed_at',
            'milestones', 'milestone_count', 'completed_milestone_count', 'progress_percent',
        ]
        read_only_fields = ['user', 'created_at', 'completed_at']
