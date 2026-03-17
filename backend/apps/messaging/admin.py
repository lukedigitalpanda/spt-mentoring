from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportMixin
from import_export import resources, fields
from .models import Conversation, Message, MassMessage, AbuseReport


class FormFixMixin:
    """Injects form_fix.css as the very last stylesheet on change pages."""
    class Media:
        css = {'all': ('admin/css/form_fix.css',)}


# ── Export resources ───────────────────────────────────────────────────────────

class MessageResource(resources.ModelResource):
    sender_name     = fields.Field(attribute='sender__full_name',               column_name='Sender')
    conversation_id = fields.Field(attribute='conversation_id',                 column_name='Conversation ID')
    subject         = fields.Field(attribute='conversation__subject',           column_name='Subject')
    conv_type       = fields.Field(attribute='conversation__conversation_type', column_name='Type')
    participants    = fields.Field(column_name='Participants')

    class Meta:
        model        = Message
        fields       = ('id', 'sender_name', 'conversation_id', 'subject', 'conv_type',
                        'body', 'sent_at', 'status', 'moderation_note', 'participants')
        export_order = ('id', 'sent_at', 'sender_name', 'conversation_id', 'subject',
                        'conv_type', 'body', 'status', 'moderation_note', 'participants')

    def dehydrate_participants(self, message):
        return ', '.join(p.full_name for p in message.conversation.participants.all())


class ConversationResource(resources.ModelResource):
    participant_names = fields.Field(column_name='Participants')
    message_count     = fields.Field(column_name='Messages')

    class Meta:
        model        = Conversation
        fields       = ('id', 'conversation_type', 'subject', 'created_at',
                        'participant_names', 'message_count')
        export_order = ('id', 'created_at', 'conversation_type', 'subject',
                        'participant_names', 'message_count')

    def dehydrate_participant_names(self, conv):
        return ', '.join(p.full_name for p in conv.participants.all())

    def dehydrate_message_count(self, conv):
        return conv.messages.count()


# ── Inline ─────────────────────────────────────────────────────────────────────

class MessageInline(admin.StackedInline):
    model            = Message
    fields           = ['sender', 'sent_at', 'status', 'body', 'moderation_note']
    readonly_fields  = ['sender', 'body', 'sent_at']
    extra            = 0
    ordering         = ['sent_at']
    can_delete       = False
    show_change_link = True


# ── Conversation ───────────────────────────────────────────────────────────────

@admin.register(Conversation)
class ConversationAdmin(FormFixMixin, ExportMixin, admin.ModelAdmin):
    resource_classes = [ConversationResource]
    list_display     = ['id', 'conversation_type', 'subject', 'participant_list', 'message_count', 'created_at']
    list_filter      = ['conversation_type']
    search_fields    = ['subject', 'participants__first_name', 'participants__last_name', 'participants__email']
    readonly_fields  = ['created_at', 'participant_list']
    inlines          = [MessageInline]

    def participant_list(self, obj):
        return ', '.join(p.full_name for p in obj.participants.all())
    participant_list.short_description = 'Participants'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


# ── Message ────────────────────────────────────────────────────────────────────

@admin.register(Message)
class MessageAdmin(FormFixMixin, ExportMixin, admin.ModelAdmin):
    resource_classes = [MessageResource]
    list_display     = ['id', 'sender', 'conversation', 'body_preview', 'status', 'moderation_note', 'sent_at']
    list_filter      = ['status', 'sent_at']
    search_fields    = ['body', 'sender__first_name', 'sender__last_name', 'sender__email']
    readonly_fields  = ['sender', 'conversation', 'body', 'sent_at', 'attachment', 'moderation_note']
    date_hierarchy   = 'sent_at'
    actions          = ['approve_flagged', 'reject_flagged', 'mark_delivered', 'mark_flagged', 'mark_blocked']

    def body_preview(self, obj):
        return obj.body[:80] + ('…' if len(obj.body) > 80 else '')
    body_preview.short_description = 'Message'

    @admin.action(description='✅ Approve flagged messages (deliver to recipient)')
    def approve_flagged(self, request, queryset):
        from apps.moderation.service import ModerationService
        approved = 0
        for msg in queryset.filter(status=Message.Status.FLAGGED):
            ModerationService.approve(msg, request.user, notes='Approved via bulk admin action')
            approved += 1
        skipped = queryset.exclude(status=Message.Status.FLAGGED).count()
        note = f'{approved} message(s) approved and delivered.'
        if skipped:
            note += f' {skipped} skipped (not flagged).'
        self.message_user(request, note)

    @admin.action(description='❌ Reject flagged messages (block permanently)')
    def reject_flagged(self, request, queryset):
        from apps.moderation.service import ModerationService
        rejected = 0
        for msg in queryset.filter(status=Message.Status.FLAGGED):
            ModerationService.reject(msg, request.user, notes='Rejected via bulk admin action')
            rejected += 1
        skipped = queryset.exclude(status=Message.Status.FLAGGED).count()
        note = f'{rejected} message(s) rejected.'
        if skipped:
            note += f' {skipped} skipped (not flagged).'
        self.message_user(request, note)

    @admin.action(description='Mark selected as delivered')
    def mark_delivered(self, request, queryset):
        queryset.update(status=Message.Status.DELIVERED)

    @admin.action(description='Mark selected as flagged')
    def mark_flagged(self, request, queryset):
        queryset.update(status=Message.Status.FLAGGED)

    @admin.action(description='Mark selected as blocked')
    def mark_blocked(self, request, queryset):
        queryset.update(status=Message.Status.BLOCKED)


# ── Mass Message ───────────────────────────────────────────────────────────────

@admin.register(MassMessage)
class MassMessageAdmin(admin.ModelAdmin):
    list_display      = ['id', 'subject', 'sender', 'role_summary', 'status', 'recipient_count', 'sent_at']
    list_filter       = ['status', 'sent_at']
    search_fields     = ['subject', 'body', 'sender__email']
    readonly_fields   = ['sender', 'status', 'sent_at', 'recipient_count', 'send_panel']
    filter_horizontal = ['recipient_programmes', 'recipient_cohorts']
    actions           = ['send_now']

    fieldsets = (
        ('Message', {
            'fields': ('subject', 'body', 'send_from_email'),
        }),
        ('Recipients', {
            'description': (
                'Select roles, then optionally narrow by programme and/or cohort. '
                'Leave programmes and cohorts blank to reach all users of the selected roles.'
            ),
            'fields': ('recipient_roles', 'recipient_programmes', 'recipient_cohorts'),
        }),
        ('Status', {
            'fields': ('sender', 'status', 'sent_at', 'recipient_count', 'send_panel'),
        }),
    )

    def role_summary(self, obj):
        roles = obj.recipient_roles or []
        return ', '.join(roles) if roles else '—'
    role_summary.short_description = 'Roles'

    def send_panel(self, obj):
        if not obj.pk:
            return '—'
        if obj.status == MassMessage.Status.SENT:
            return format_html(
                '<span style="color:green;font-weight:700;">✓ Sent to {} recipient{}</span>',
                obj.recipient_count,
                's' if obj.recipient_count != 1 else '',
            )
        return format_html(
            '<a class="button" href="send/" '
            'style="background:#e01e8c;color:#fff;padding:6px 18px;border-radius:6px;'
            'font-weight:700;text-decoration:none;">'
            '▶ Send this message now</a>'
        )
    send_panel.short_description = 'Send'

    def save_model(self, request, obj, form, change):
        if not obj.pk or not obj.sender_id:
            obj.sender = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/send/',
                self.admin_site.admin_view(self.send_view),
                name='messaging_massmessage_send',
            ),
        ]
        return custom + urls

    def send_view(self, request, pk):
        from django.shortcuts import redirect
        from .tasks import send_mass_message_task

        try:
            msg = MassMessage.objects.get(pk=pk)
        except MassMessage.DoesNotExist:
            self.message_user(request, 'Mass message not found.', level='error')
            return redirect('..')

        if msg.status == MassMessage.Status.SENT:
            self.message_user(request, 'This message has already been sent.', level='warning')
        else:
            send_mass_message_task(msg.pk)
            msg.refresh_from_db()
            self.message_user(
                request,
                f'"{msg.subject}" sent successfully to {msg.recipient_count} recipient(s).',
            )
        return redirect(f'../{pk}/change/')

    @admin.action(description='Send selected mass messages now')
    def send_now(self, request, queryset):
        from .tasks import send_mass_message_task
        sent = 0
        for msg in queryset.filter(status=MassMessage.Status.DRAFT):
            send_mass_message_task(msg.pk)
            sent += 1
        skipped = queryset.count() - sent
        note = f'{sent} message(s) sent.'
        if skipped:
            note += f' {skipped} skipped (already sent).'
        self.message_user(request, note)


# ── Abuse Report ───────────────────────────────────────────────────────────────

@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display    = ['id', 'reporter', 'reported_user', 'status', 'created_at']
    list_filter     = ['status']
    readonly_fields = ['reporter', 'reported_user', 'message', 'created_at']
