from rest_framework import serializers
from .models import Conversation, Message, MessageRead, MassMessage, AbuseReport
from apps.users.validators import validate_message_attachment


# Identity of the system account send_mass_message_task (and the admin
# reply panels) send broadcasts from - see apps/messaging/tasks.py and
# apps/messaging/admin.py get_or_create_arkwright(). Matched by email, not
# id: this must stay a lookup rather than a get_or_create() so serialising
# a message (a read) can never have the side effect of creating the
# account. Kept as a literal here to mirror the existing convention used
# throughout this app (tasks.py, admin.py, views.py, tests.py all match
# 'arkwright@spt.org' the same way) rather than introducing a new shared
# constant this task doesn't otherwise need.
ARKWRIGHT_EMAIL = 'arkwright@spt.org'


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    is_read = serializers.SerializerMethodField()
    is_broadcast = serializers.SerializerMethodField()
    attachment = serializers.FileField(validators=[validate_message_attachment], required=False, allow_null=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'body',
            'sent_at', 'edited_at', 'status', 'attachment', 'attachment_name',
            'is_read', 'is_broadcast',
        ]
        read_only_fields = ['sent_at', 'edited_at', 'status', 'sender']

    def get_is_read(self, obj):
        request = self.context.get('request')
        if request:
            return obj.reads.filter(user=request.user).exists()
        return False

    def get_is_broadcast(self, obj):
        # True for messages in a mass_message conversation sent by the
        # Arkwright system account. This is the sole signal the frontend
        # uses to decide whether a message body is trusted,
        # backend-sanitised HTML (safe for dangerouslySetInnerHTML) versus
        # ordinary unsanitised chat text - get it wrong here and that
        # becomes an XSS hole, so it keys off identity + conversation
        # type, never off position/index, which a history-loading WS race
        # or a second human participant in the thread can invalidate.
        #
        # Known accepted residual (self-XSS at the current topology): a
        # mass_message conversation is always exactly Arkwright + one
        # recipient, and Arkwright is also the identity used for admin
        # reply-panel replies (apps/messaging/admin.py
        # arkwright_reply_panel) - those replies are free-typed, NOT run
        # through sanitise_rich_text(), yet also serialise is_broadcast
        # True because they share the same sender+conversation_type. The
        # actor who can trigger unsanitised-HTML rendering this way is
        # therefore limited to an admin operating as Arkwright (not an
        # arbitrary recipient) - a materially smaller risk than the
        # position-based bug this replaces, but not a full closure. If a
        # mass_message conversation ever gains a second human participant,
        # or the admin reply panel needs real rich text, that reply path
        # would need its own sanitise_rich_text() call before this
        # trade-off remains acceptable.
        return (
            obj.conversation.conversation_type == Conversation.ConversationType.MASS_MESSAGE
            and obj.sender_id is not None
            and obj.sender.email == ARKWRIGHT_EMAIL
        )


class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_names = serializers.SerializerMethodField()
    participant_details = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'participants', 'participant_names', 'participant_details',
            'subject', 'created_at', 'is_private', 'cohort', 'replies_enabled',
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

    def get_participant_details(self, obj):
        return [
            {'id': p.pk, 'full_name': p.full_name, 'first_name': p.first_name, 'last_name': p.last_name}
            for p in obj.participants.all()
        ]


class MassMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MassMessage
        fields = '__all__'
        read_only_fields = ['sent_at', 'status', 'recipient_count', 'sender']

    def create(self, validated_data):
        # ManyToMany fields must be set after save
        programmes = validated_data.pop('recipient_programmes', [])
        cohorts = validated_data.pop('recipient_cohorts', [])
        instance = super().create(validated_data)
        if programmes:
            instance.recipient_programmes.set(programmes)
        if cohorts:
            instance.recipient_cohorts.set(cohorts)
        return instance


class AbuseReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True)

    class Meta:
        model = AbuseReport
        fields = '__all__'
        read_only_fields = ['created_at', 'reporter']
