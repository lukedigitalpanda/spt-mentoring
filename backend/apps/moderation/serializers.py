from rest_framework import serializers
from .models import BlockedTerm, FlaggedTerm, ModerationLog


class BlockedTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedTerm
        fields = '__all__'
        read_only_fields = ['added_by', 'added_at']


class FlaggedTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlaggedTerm
        fields = '__all__'
        read_only_fields = ['added_by', 'added_at']


class ModerationLogSerializer(serializers.ModelSerializer):
    actioned_by_name = serializers.CharField(source='actioned_by.full_name', read_only=True)

    class Meta:
        model = ModerationLog
        fields = '__all__'
