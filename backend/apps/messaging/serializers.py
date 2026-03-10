from rest_framework import serializers
from .models import Conversation, Message, MessageRead, MassMessage, AbuseReport


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'body',
            'sent_at', 'status', 'attachment', 'attachment_name', 'is_read',
        ]
        read_only_fields = ['sent_at', 'status', 'sender']

    def get_is_read(self, obj):
        request = self.context.get('request')
        if request:
            return obj.reads.filter(user=request.user).exists()
        return False


class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_names = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'participants', 'participant_names',
            'subject', 'created_at', 'is_private', 'cohort',
            'last_message', 'unread_count',
        ]

    def get_last_message(self, obj):
        msg = obj.last_message
        if msg:
            return {'id': msg.pk, 'body': msg.body[:100], 'sent_at': msg.sent_at, 'sender': msg.sender.full_name}
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request:
            return obj.messages.filter(
                status=Message.Status.DELIVERED
            ).exclude(reads__user=request.user).count()
        return 0

    def get_participant_names(self, obj):
        return [p.full_name for p in obj.participants.all()]


class MassMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MassMessage
        fields = '__all__'
        read_only_fields = ['sent_at', 'status', 'recipient_count', 'sender']


class AbuseReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True)

    class Meta:
        model = AbuseReport
        fields = '__all__'
        read_only_fields = ['created_at', 'reporter']
