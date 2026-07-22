from django import forms
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

    def save_model(self, request, obj, form, change):
        if not obj.sender_id:
            obj.sender = request.user
        super().save_model(request, obj, form, change)


# ── Custom list filters ────────────────────────────────────────────────────────

class MessageStatusFilter(admin.SimpleListFilter):
    """TC-04: Status filter that excludes the transient PENDING state.
    Showing PENDING in the filter sidebar was confusing — admins cannot set
    it manually and it should never persist after screening.  Excluding it
    from the filter options removes the temptation to click it and see an
    empty list (which looked like messages were 'disappearing').
    """
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            (v, l) for v, l in Message.Status.choices
            if v != Message.Status.PENDING
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class SupportConversationFilter(admin.SimpleListFilter):
    """Filter conversations to show only inbound support requests.

    ISS-C: Restricts to DIRECT conversations with subject='Support' involving
    the Arkwright account.  This excludes outgoing mass-message conversations
    which are also DIRECT + Arkwright but have the mass-message subject instead.
    """
    title = 'support conversations'
    parameter_name = 'support'

    def lookups(self, request, model_admin):
        return [('yes', 'Inbound support requests only')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                participants__email='arkwright@spt.org',
                conversation_type=Conversation.ConversationType.DIRECT,
                subject='Support',
            )
        return queryset


# ── Start-a-conversation (admin-initiated direct message) ───────────────────────

def get_or_create_arkwright():
    """Fetch (or lazily create) the Arkwright support account used as the sender
    for admin-originated messages. Mirrors the account used by contact_support
    and the reply panels so recipients see one consistent support identity."""
    from apps.users.models import User
    arkwright, created = User.objects.get_or_create(
        email='arkwright@spt.org',
        defaults={
            'username': 'arkwright',
            'first_name': 'Arkwright',
            'last_name': '',
            'role': 'admin',
            'is_active': True,
            'notification_email': False,
            'is_verified': True,
        },
    )
    if created:
        arkwright.set_unusable_password()
        arkwright.save()
    return arkwright


class StartConversationForm(forms.Form):
    """Admin form to open a brand-new direct message to a single user."""
    recipient = forms.ModelChoiceField(
        queryset=None,  # populated in __init__ to avoid import-time DB access
        label='Send to',
        help_text='The scholar, mentor or sponsor who should receive this message.',
    )
    subject = forms.CharField(
        max_length=255, required=False,
        help_text='Optional — shown as the thread title. Ignored if a thread with this person already exists.',
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        label='Message',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.users.models import User
        self.fields['recipient'].queryset = (
            User.objects.filter(is_active=True)
            .exclude(email='arkwright@spt.org')
            .order_by('last_name', 'first_name')
        )
        self.fields['recipient'].label_from_instance = (
            lambda u: f'{u.full_name} — {u.get_role_display()} ({u.email})'
        )

    def clean_body(self):
        body = (self.cleaned_data.get('body') or '').strip()
        if not body:
            raise forms.ValidationError('Please enter a message to send.')
        return body


# ── Conversation ───────────────────────────────────────────────────────────────

@admin.register(Conversation)
class ConversationAdmin(FormFixMixin, ExportMixin, admin.ModelAdmin):
    # ExportMixin owns change_list_template (it renders the Export button and
    # stashes any change_list_template as the root parent, whose block overrides
    # then get dropped by the dynamic-extends chain). The supported hook for
    # customising the export-enabled changelist is import_export_change_list_template,
    # which becomes the actual leaf template — so our "Start new message" button
    # renders reliably. See templates/admin/messaging/conversation_changelist.html.
    import_export_change_list_template = 'admin/messaging/conversation_changelist.html'
    resource_classes = [ConversationResource]
    list_display     = ['id', 'conversation_type', 'subject', 'participant_list', 'message_count', 'support_status', 'created_at']
    list_filter      = ['conversation_type', SupportConversationFilter]
    search_fields    = ['subject', 'participants__first_name', 'participants__last_name', 'participants__email']
    readonly_fields  = ['created_at', 'participant_list', 'arkwright_reply_panel', 'resolve_panel']
    inlines          = [MessageInline]

    fieldsets = (
        (None, {
            'fields': ('conversation_type', 'subject', 'participant_list', 'replies_enabled', 'created_at'),
        }),
        ('Support Status', {
            'description': (
                'For support conversations: track whether the exchange has been resolved. '
                'Resolved conversations are excluded from the admin homepage support counter.'
            ),
            'fields': ('support_status', 'resolve_panel'),
        }),
        ('Reply as Arkwright', {
            'description': (
                'Use this panel to send a reply into this conversation as the Arkwright support account. '
                'The message will appear in the recipient\'s message thread immediately.'
            ),
            'fields': ('arkwright_reply_panel',),
        }),
    )

    def participant_list(self, obj):
        return ', '.join(p.full_name for p in obj.participants.all())
    participant_list.short_description = 'Participants'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'

    def arkwright_reply_panel(self, obj):
        if not obj.pk:
            return '—'
        from django.urls import reverse
        reply_url = reverse('admin:messaging_conversation_reply', args=[obj.pk])
        # Renders outside any <form> tag so there is no nested-form issue.
        # Uses fetch() to POST directly to reply_view, which returns JSON.
        return format_html(
            '<div>'
            '<textarea id="ark-body-{pk}" rows="3" placeholder="Type your reply here…" '
            'style="width:100%;max-width:520px;border:1px solid #d1c4e9;border-radius:8px;'
            'padding:8px 10px;font-size:0.82rem;resize:vertical;"></textarea><br>'
            '<button type="button" id="ark-btn-{pk}" data-url="{url}" '
            'style="margin-top:8px;background:#e01e8c;color:#fff;'
            'padding:6px 18px;border-radius:6px;font-weight:700;border:none;cursor:pointer;">'
            '▶ Send reply as Arkwright</button>'
            '<span id="ark-status-{pk}" style="margin-left:10px;font-size:0.82rem;"></span>'
            '</div>'
            '<script>(function(){{'
            'var btn=document.getElementById("ark-btn-{pk}");'
            'btn.addEventListener("click",function(){{'
            'var body=document.getElementById("ark-body-{pk}").value.trim();'
            'if(!body){{alert("Please enter a reply.");return;}}'
            'var csrf="",m=document.cookie.match(/csrftoken=([^;]+)/);'
            'if(m)csrf=decodeURIComponent(m[1]);'
            'btn.disabled=true;'
            'var st=document.getElementById("ark-status-{pk}");'
            'st.style.color="";st.textContent="Sending\u2026";'
            'fetch(btn.dataset.url,{{'
            'method:"POST",'
            'headers:{{"X-CSRFToken":csrf,"X-Requested-With":"XMLHttpRequest",'
            '"Content-Type":"application/x-www-form-urlencoded"}},'
            'body:"body="+encodeURIComponent(body)'
            '}}).then(function(r){{return r.json();}})'
            '.then(function(d){{'
            'btn.disabled=false;'
            'if(d.status==="ok"){{'
            'document.getElementById("ark-body-{pk}").value="";'
            'st.style.color="green";st.textContent="\u2713 Sent!";'
            'setTimeout(function(){{st.textContent="";}},3000);'
            '}}else{{st.style.color="red";st.textContent="Error: "+(d.error||"Unknown");}}'
            '}})'
            '.catch(function(){{'
            'btn.disabled=false;st.style.color="red";st.textContent="Network error.";'
            '}});'
            '}});'
            '}})();</script>',
            pk=obj.pk,
            url=reply_url,
        )
    arkwright_reply_panel.short_description = 'Send reply'

    def resolve_panel(self, obj):
        """One-click button to mark a support conversation as resolved."""
        if not obj.pk:
            return '—'
        from django.urls import reverse
        if obj.support_status == Conversation.SupportStatus.RESOLVED:
            reopen_url = reverse('admin:messaging_conversation_resolve', args=[obj.pk, 'open'])
            return format_html(
                '<span style="color:green;font-weight:700;">✓ Resolved</span> &nbsp;'
                '<a href="{}" style="font-size:0.8rem;color:#7c3aed;">Reopen</a>',
                reopen_url,
            )
        resolve_url = reverse('admin:messaging_conversation_resolve', args=[obj.pk, 'resolved'])
        return format_html(
            '<a href="{}" class="button" '
            'style="background:#16a34a;color:#fff;padding:5px 16px;border-radius:6px;'
            'font-weight:700;text-decoration:none;display:inline-block;">'
            '✓ Mark as Resolved</a>',
            resolve_url,
        )
    resolve_panel.short_description = 'Resolve'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path(
                'start-conversation/',
                self.admin_site.admin_view(self.start_conversation_view),
                name='messaging_conversation_start',
            ),
            path(
                '<int:pk>/reply/',
                self.admin_site.admin_view(self.reply_view),
                name='messaging_conversation_reply',
            ),
            path(
                '<int:pk>/set-support-status/<str:new_status>/',
                self.admin_site.admin_view(self.set_support_status_view),
                name='messaging_conversation_resolve',
            ),
        ]
        return custom + urls

    def start_conversation_view(self, request):
        """Admin-initiated direct message: pick a recipient, type a message, and
        it is sent as the Arkwright support account. Reuses an existing Arkwright
        thread with that person if one exists so we don't spawn duplicates."""
        from django.contrib import messages as msg
        from django.shortcuts import redirect
        from django.template.response import TemplateResponse
        from django.urls import reverse
        from .models import Message, MessageRead

        if request.method == 'POST':
            form = StartConversationForm(request.POST)
            if form.is_valid():
                recipient = form.cleaned_data['recipient']
                subject = (form.cleaned_data.get('subject') or '').strip()
                body = form.cleaned_data['body']
                arkwright = get_or_create_arkwright()

                conv = (
                    Conversation.objects
                    .filter(participants=arkwright)
                    .filter(participants=recipient)
                    .filter(conversation_type=Conversation.ConversationType.DIRECT)
                    .first()
                )
                if conv is None:
                    conv = Conversation.objects.create(
                        conversation_type=Conversation.ConversationType.DIRECT,
                        subject=subject,
                    )
                    conv.participants.add(arkwright, recipient)

                message = Message.objects.create(
                    conversation=conv,
                    sender=arkwright,
                    body=body,
                    status=Message.Status.DELIVERED,
                )
                MessageRead.objects.create(message=message, user=arkwright)
                # The recipient's in-app notification + email are dispatched by the
                # post_save signal that fires on delivered messages — no extra work here.

                msg.success(request, f'Message sent to {recipient.full_name}.')
                return redirect(reverse('admin:messaging_conversation_change', args=[conv.pk]))
        else:
            form = StartConversationForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Start a new message',
            'form': form,
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/messaging/start_conversation.html', context)

    def set_support_status_view(self, request, pk, new_status):
        from django.shortcuts import redirect
        from django.urls import reverse
        valid = [s for s, _ in Conversation.SupportStatus.choices]
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            self.message_user(request, 'Conversation not found.', level='error')
            return redirect(reverse('admin:messaging_conversation_changelist'))
        if new_status not in valid:
            self.message_user(request, f'Invalid status: {new_status}', level='error')
            return redirect(reverse('admin:messaging_conversation_change', args=[pk]))
        conv.support_status = new_status
        conv.save(update_fields=['support_status'])
        label = dict(Conversation.SupportStatus.choices).get(new_status, new_status)
        self.message_user(request, f'Support conversation marked as {label}.')
        return redirect(reverse('admin:messaging_conversation_change', args=[pk]))

    def reply_view(self, request, pk):
        from django.shortcuts import redirect
        from django.http import JsonResponse
        from django.urls import reverse
        from .models import Message, MessageRead

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if request.method != 'POST':
            return redirect(reverse('admin:messaging_conversation_change', args=[pk]))

        body = request.POST.get('body', '').strip()
        if not body:
            if is_ajax:
                return JsonResponse({'error': 'Reply body cannot be empty.'}, status=400)
            self.message_user(request, 'Reply body cannot be empty.', level='error')
            return redirect(reverse('admin:messaging_conversation_change', args=[pk]))

        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            if is_ajax:
                return JsonResponse({'error': 'Conversation not found.'}, status=404)
            self.message_user(request, 'Conversation not found.', level='error')
            return redirect(reverse('admin:messaging_conversation_changelist'))

        from apps.users.models import User
        arkwright, _ = User.objects.get_or_create(
            email='arkwright@spt.org',
            defaults={
                'username': 'arkwright',
                'first_name': 'Arkwright',
                'last_name': '',
                'role': 'admin',
                'is_active': True,
                'notification_email': False,
                'is_verified': True,
            },
        )

        msg = Message.objects.create(
            conversation=conv,
            sender=arkwright,
            body=body,
            status=Message.Status.DELIVERED,
        )
        MessageRead.objects.create(message=msg, user=arkwright)

        if is_ajax:
            return JsonResponse({'status': 'ok'})
        self.message_user(request, 'Reply sent successfully via Arkwright.')
        return redirect(reverse('admin:messaging_conversation_change', args=[pk]))


# ── Message ────────────────────────────────────────────────────────────────────

@admin.register(Message)
class MessageAdmin(FormFixMixin, ExportMixin, admin.ModelAdmin):
    resource_classes = [MessageResource]
    list_display     = ['id', 'sender', 'conversation', 'body_preview', 'status_display', 'review_actions', 'moderation_note', 'sent_at']
    list_filter      = [MessageStatusFilter, 'sent_at']
    search_fields    = ['body', 'sender__first_name', 'sender__last_name', 'sender__email']
    # TC-03/TC-04: 'status' is NOT in readonly_fields so admins can change it,
    # but PENDING is excluded from the choices (it is transient and should never
    # be set manually — it indicates a screening pipeline error if seen).
    readonly_fields  = ['sender', 'conversation', 'body', 'sent_at', 'attachment', 'moderation_note', 'moderation_guide', 'reply_to_sender_panel']
    date_hierarchy   = 'sent_at'
    actions          = ['approve_flagged', 'reject_flagged', 'mark_delivered', 'mark_flagged', 'mark_blocked']
    fieldsets = (
        ('Message', {
            'fields': ('sender', 'conversation', 'body', 'attachment', 'sent_at', 'reply_to_sender_panel'),
        }),
        ('Moderation', {
            'description': (
                '<strong>Status guide:</strong> '
                '<span style="color:#e01e8c;font-weight:600;">Flagged for Review</span> — message matched a '
                'Flagged Term and is held for admin approval or rejection. Use the ✅ Approve or ❌ Reject '
                'bulk actions, or change the status below. '
                '<span style="color:#dc2626;font-weight:600;">Blocked</span> — matched a Blocked Term or '
                'rejected by an admin; never delivered to recipients. '
                '<span style="color:#16a34a;font-weight:600;">Delivered</span> — passed all checks and is '
                'visible to all conversation participants. '
                '<span style="color:#6b7280;font-weight:600;">Deleted</span> — soft-deleted; hidden from participants. '
                '<em>Note: "Pending Moderation" is a transient internal state — if you see it, investigate '
                'for a screening pipeline error. It cannot be set manually.</em>'
            ),
            'fields': ('status', 'moderation_note', 'moderation_guide'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'status' in form.base_fields:
            # TC-04: Remove PENDING from editable choices — it is a transient
            # screening state that should never be set manually by admins.
            form.base_fields['status'].choices = [
                (v, l) for v, l in Message.Status.choices
                if v != Message.Status.PENDING
            ]
        return form

    def status_display(self, obj):
        colours = {
            'pending':   '#f59e0b',
            'flagged':   '#e01e8c',
            'blocked':   '#dc2626',
            'delivered': '#16a34a',
            'deleted':   '#6b7280',
        }
        labels = {
            'pending':   'Pending',
            'flagged':   'Flagged for Review',
            'blocked':   'Blocked',
            'delivered': 'Delivered',
            'deleted':   'Deleted',
        }
        colour = colours.get(obj.status, '#6b7280')
        label  = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color:{};font-weight:600;">● {}</span>', colour, label
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def reply_to_sender_panel(self, obj):
        """TC-03: Inline reply form so admins can send a contextual response to the
        message sender without leaving the message detail page.  Posts to the
        ConversationAdmin reply_view endpoint which handles the Arkwright send."""
        if not obj.pk or not obj.conversation_id:
            return '—'
        from django.urls import reverse
        reply_url = reverse('admin:messaging_conversation_reply', args=[obj.conversation_id])
        pk = obj.pk  # use message pk for unique element IDs
        # Uses fetch() to avoid the nested-form issue (this panel is rendered inside
        # the MessageAdmin change <form>; a nested <form> would be ignored by the browser).
        return format_html(
            '<div>'
            '<textarea id="msg-body-{pk}" rows="3" placeholder="Type your reply here…" '
            'style="width:100%;max-width:520px;border:1px solid #d1c4e9;border-radius:8px;'
            'padding:8px 10px;font-size:0.82rem;resize:vertical;box-sizing:border-box;"></textarea><br>'
            '<button type="button" id="msg-btn-{pk}" data-url="{url}" '
            'style="margin-top:8px;background:#7c3aed;color:#fff;'
            'padding:6px 18px;border-radius:6px;font-weight:700;border:none;cursor:pointer;">'
            '↩ Send reply as Arkwright</button>'
            '<span id="msg-status-{pk}" style="margin-left:10px;font-size:0.82rem;"></span>'
            '</div>'
            '<script>(function(){{'
            'var btn=document.getElementById("msg-btn-{pk}");'
            'btn.addEventListener("click",function(){{'
            'var body=document.getElementById("msg-body-{pk}").value.trim();'
            'if(!body){{alert("Please enter a reply.");return;}}'
            'var csrf="",m=document.cookie.match(/csrftoken=([^;]+)/);'
            'if(m)csrf=decodeURIComponent(m[1]);'
            'btn.disabled=true;'
            'var st=document.getElementById("msg-status-{pk}");'
            'st.style.color="";st.textContent="Sending\u2026";'
            'fetch(btn.dataset.url,{{'
            'method:"POST",'
            'headers:{{"X-CSRFToken":csrf,"X-Requested-With":"XMLHttpRequest",'
            '"Content-Type":"application/x-www-form-urlencoded"}},'
            'body:"body="+encodeURIComponent(body)'
            '}}).then(function(r){{return r.json();}})'
            '.then(function(d){{'
            'btn.disabled=false;'
            'if(d.status==="ok"){{'
            'document.getElementById("msg-body-{pk}").value="";'
            'st.style.color="green";st.textContent="\u2713 Sent!";'
            'setTimeout(function(){{st.textContent="";}},3000);'
            '}}else{{st.style.color="red";st.textContent="Error: "+(d.error||"Unknown");}}'
            '}})'
            '.catch(function(){{'
            'btn.disabled=false;st.style.color="red";st.textContent="Network error.";'
            '}});'
            '}});'
            '}})();</script>',
            pk=pk,
            url=reply_url,
        )
    reply_to_sender_panel.short_description = 'Reply to sender'

    def moderation_guide(self, obj):
        from django.utils.html import format_html
        statuses = {
            'pending': ('#f59e0b', 'Transient — message is being screened. If stuck here, investigate for screening errors.'),
            'flagged': ('#e01e8c', 'Held for review — use ✅ Approve or ❌ Reject actions to resolve.'),
            'blocked': ('#dc2626', 'Permanently blocked — sender has been notified.'),
            'delivered': ('#16a34a', 'Delivered — visible to all conversation participants.'),
            'deleted': ('#6b7280', 'Soft-deleted — hidden from all participants.'),
        }
        color, desc = statuses.get(obj.status, ('#6b7280', ''))
        return format_html(
            '<span style="color:{};font-weight:600;">●</span> <span style="color:#555;">{}</span>',
            color, desc,
        )
    moderation_guide.short_description = 'Status meaning'

    def body_preview(self, obj):
        return obj.body[:160] + ('…' if len(obj.body) > 160 else '')
    body_preview.short_description = 'Message'

    # ── Moderation queue: per-row approve / reject (ADM-02) ──────────────────

    def review_actions(self, obj):
        """Inline Approve / Reject buttons shown directly in the flagged queue so
        an admin can action a held message without hunting through bulk actions."""
        if obj.status != Message.Status.FLAGGED:
            return format_html('<span style="color:#bbb;">—</span>')
        from django.urls import reverse
        approve_url = reverse('admin:messaging_message_quick_moderate', args=[obj.pk, 'approve'])
        reject_url = reverse('admin:messaging_message_quick_moderate', args=[obj.pk, 'reject'])
        return format_html(
            '<a href="{approve}" style="display:inline-block;padding:2px 10px;border-radius:4px;'
            'background:#2e7d32;color:#fff;font-size:11px;text-decoration:none;margin-right:4px;">'
            '✅ Approve</a>'
            '<a href="{reject}" style="display:inline-block;padding:2px 10px;border-radius:4px;'
            'background:#c62828;color:#fff;font-size:11px;text-decoration:none;">'
            '❌ Reject</a>',
            approve=approve_url,
            reject=reject_url,
        )
    review_actions.short_description = 'Quick action'

    def _redirect_to_flagged_queue(self, request):
        """Send the admin back to the flagged queue after actioning a message."""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(
            reverse('admin:messaging_message_changelist') + '?status=flagged'
        )

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/moderate/<str:action>/',
                self.admin_site.admin_view(self.quick_moderate_view),
                name='messaging_message_quick_moderate',
            ),
        ]
        return custom + urls

    def quick_moderate_view(self, request, pk, action):
        from apps.moderation.service import ModerationService
        try:
            msg = Message.objects.get(pk=pk)
        except Message.DoesNotExist:
            self.message_user(request, 'Message not found.', level='error')
            return self._redirect_to_flagged_queue(request)

        if msg.status != Message.Status.FLAGGED:
            self.message_user(
                request,
                f'Message #{pk} is no longer awaiting review (status: {msg.get_status_display()}).',
                level='warning',
            )
            return self._redirect_to_flagged_queue(request)

        if action == 'approve':
            ModerationService.approve(msg, request.user, notes='Approved via moderation queue')
            self.message_user(request, f'Message #{pk} approved and delivered to the recipient.')
        elif action == 'reject':
            ModerationService.reject(
                msg, request.user,
                notes='Your message was reviewed and blocked by a moderator as it did not meet our community guidelines.',
            )
            self.message_user(request, f'Message #{pk} rejected; it will not be delivered and the sender has been notified.')
        else:
            self.message_user(request, f'Unknown action: {action}', level='error')
        return self._redirect_to_flagged_queue(request)

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

    @admin.action(description='❌ Reject flagged messages (block permanently, notify sender)')
    def reject_flagged(self, request, queryset):
        # TC-03: After rejection the message status becomes BLOCKED. Clear any
        # active "status=flagged" filter so the rejected messages remain visible
        # in the list rather than disappearing. We do this by returning an
        # HttpResponseRedirect to the changelist without the filter applied.
        from apps.moderation.service import ModerationService
        rejected = 0
        for msg in queryset.filter(status=Message.Status.FLAGGED):
            ModerationService.reject(
                msg, request.user,
                notes='Your message was reviewed and blocked by a moderator as it did not meet our community guidelines.',
            )
            rejected += 1
        skipped = queryset.exclude(status=Message.Status.FLAGGED).count()
        note = f'{rejected} message(s) rejected and sender(s) notified.'
        if skipped:
            note += f' {skipped} skipped (not flagged).'
        self.message_user(request, note)
        # Redirect to unfiltered list so blocked messages remain visible
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('admin:messaging_message_changelist'))

    @admin.action(description='Mark selected as delivered')
    def mark_delivered(self, request, queryset):
        # Only FLAGGED messages may be released this way - looping approve()
        # over BLOCKED or already-DELIVERED rows would silently reverse a
        # moderator's block decision, fire a bogus "approved" sender
        # notification, re-trigger the recipient post_save signal (duplicate
        # notification + email), and re-broadcast into the live chat thread.
        from apps.moderation.service import ModerationService
        released = 0
        for msg in queryset.filter(status=Message.Status.FLAGGED):
            ModerationService.approve(msg, request.user, notes='Bulk approved via admin')
            released += 1
        skipped = queryset.exclude(status=Message.Status.FLAGGED).count()
        note = f'{released} released, {skipped} skipped (not flagged).'
        self.message_user(request, note)

    @admin.action(description='Mark selected as flagged')
    def mark_flagged(self, request, queryset):
        queryset.update(status=Message.Status.FLAGGED)

    @admin.action(description='Mark selected as blocked')
    def mark_blocked(self, request, queryset):
        queryset.update(status=Message.Status.BLOCKED)


# ── Mass Message ───────────────────────────────────────────────────────────────

ROLE_CHOICES = [
    ('scholar', 'Scholar'),
    ('mentor', 'Mentor'),
    ('sponsor', 'Sponsor'),
    ('alumni', 'Alumni'),
]


class MassMessageAdminForm(forms.ModelForm):
    recipient_roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select one or more recipient roles.',
    )

    class Meta:
        model = MassMessage
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['recipient_roles'] = self.instance.recipient_roles or []

    def clean_recipient_roles(self):
        return list(self.cleaned_data.get('recipient_roles') or [])


@admin.register(MassMessage)
class MassMessageAdmin(admin.ModelAdmin):
    form = MassMessageAdminForm
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
        ('Reply settings', {
            'description': (
                'When "Allow replies" is enabled, recipients can reply directly to this broadcast '
                'and their reply will land in the sender\'s inbox. '
                'Disable it for one-way announcements where no reply is expected.'
            ),
            'fields': ('replies_enabled',),
        }),
        ('Send', {
            'description': (
                'Step 1: fill in the fields above and click Save. '
                'Step 2: click the Send button that appears below once the draft is saved.'
            ),
            'fields': ('sender', 'status', 'sent_at', 'recipient_count', 'send_panel'),
        }),
    )

    def role_summary(self, obj):
        roles = obj.recipient_roles or []
        return ', '.join(roles) if roles else '—'
    role_summary.short_description = 'Roles'

    def send_panel(self, obj):
        if not obj.pk:
            return format_html(
                '<span style="color:#6b7280;font-style:italic;">'
                'Save this draft first, then the Send button will appear here.'
                '</span>'
            )
        if obj.status == MassMessage.Status.SENT:
            return format_html(
                '<span style="color:green;font-weight:700;">✓ Sent to {} recipient{}</span>',
                obj.recipient_count,
                's' if obj.recipient_count != 1 else '',
            )
        if obj.status == MassMessage.Status.SENDING:
            return format_html(
                '<span style="color:#d97706;font-weight:700;">⏳ Sending in the background…</span> '
                '<span style="color:#6b7280;font-size:0.8rem;">Refresh this page in a moment to see the final recipient count.</span>'
            )
        from django.urls import reverse
        send_url = reverse('admin:messaging_massmessage_send', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" '
            'style="background:#e01e8c;color:#fff;padding:6px 18px;border-radius:6px;'
            'font-weight:700;text-decoration:none;">'
            '▶ Send this message now</a>',
            send_url,
        )
    send_panel.short_description = 'Send'

    def save_model(self, request, obj, form, change):
        if not obj.pk or not obj.sender_id:
            obj.sender = request.user
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        # MSG-06 flow: after saving a new draft, stay on the change page so the
        # admin can click Send without reopening the item.
        if not any(k in request.POST for k in ('_addanother', '_popup')):
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            self.message_user(request, 'Draft saved. Use the Send button below to send it now.')
            return HttpResponseRedirect(reverse('admin:messaging_massmessage_change', args=[obj.pk]))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        # MSG-06 flow: keep the admin on the change page after Save (instead of
        # bouncing to the list) so the save -> send flow is a single context.
        if not any(k in request.POST for k in ('_addanother', '_continue', '_saveasnew')):
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            self.message_user(request, 'Changes saved. Use the Send button below to send it now.')
            return HttpResponseRedirect(reverse('admin:messaging_massmessage_change', args=[obj.pk]))
        return super().response_change(request, obj)

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
        # MSG-06: queue the fan-out on the Celery worker and return immediately so
        # the request never hits the nginx gateway timeout. Stay on the change
        # view so the admin keeps context and can watch the status update.
        from django.shortcuts import redirect
        from django.urls import reverse
        from .tasks import send_mass_message_task

        try:
            msg = MassMessage.objects.get(pk=pk)
        except MassMessage.DoesNotExist:
            self.message_user(request, 'Mass message not found.', level='error')
            return redirect(reverse('admin:messaging_massmessage_changelist'))

        change_url = reverse('admin:messaging_massmessage_change', args=[msg.pk])

        if msg.status in (MassMessage.Status.SENDING, MassMessage.Status.SENT):
            self.message_user(
                request,
                'This message has already been sent or is currently sending.',
                level='warning',
            )
        else:
            msg.status = MassMessage.Status.SENDING
            msg.save(update_fields=['status'])
            send_mass_message_task.delay(msg.pk)
            self.message_user(
                request,
                f'"{msg.subject}" is being sent in the background. '
                'Refresh this page shortly to see the final recipient count.',
            )
        return redirect(change_url)

    @admin.action(description='Send selected mass messages now')
    def send_now(self, request, queryset):
        from .tasks import send_mass_message_task
        queued = 0
        for msg in queryset.filter(status=MassMessage.Status.DRAFT):
            msg.status = MassMessage.Status.SENDING
            msg.save(update_fields=['status'])
            send_mass_message_task.delay(msg.pk)
            queued += 1
        skipped = queryset.count() - queued
        note = f'{queued} message(s) queued for background sending.'
        if skipped:
            note += f' {skipped} skipped (already sent or sending).'
        self.message_user(request, note)


# ── Abuse Report ───────────────────────────────────────────────────────────────

@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display    = ['id', 'reporter', 'reported_user', 'description_preview', 'reported_message_preview', 'status', 'created_at', 'resolved_by']
    list_filter     = ['status', 'created_at']
    search_fields   = ['reporter__email', 'reported_user__email', 'description', 'reported_content']
    readonly_fields = ['reporter', 'reported_user', 'message', 'reported_message_body', 'created_at']
    actions         = ['mark_under_review', 'mark_resolved']
    # P2-6: reporter, reported user and the reported content must all be
    # visible together on the first screen — no tab-hopping.
    fieldsets = (
        ('Report', {
            'fields': ('reporter', 'reported_user', 'reported_message_body', 'description', 'message', 'created_at'),
        }),
        ('Resolution', {
            'description': (
                'Update status and add resolution notes once the report has been reviewed. '
                '"Open" = not yet reviewed. '
                '"Under Review" = being investigated. '
                '"Resolved" = investigation complete.'
            ),
            'fields': ('status', 'resolved_by', 'resolved_at', 'resolution_notes'),
        }),
    )

    def _reported_text(self, obj):
        """Best available record of what was reported: the snapshot taken at
        report time, falling back to the linked message's current body."""
        if obj.reported_content:
            return obj.reported_content
        if obj.message:
            return obj.message.body
        return ''

    def description_preview(self, obj):
        return obj.description[:60] + ('…' if len(obj.description) > 60 else '')
    description_preview.short_description = 'Description'

    def reported_message_preview(self, obj):
        text = self._reported_text(obj)
        if text:
            return text[:60] + ('…' if len(text) > 60 else '')
        return 'no content captured'
    reported_message_preview.short_description = 'Reported content'

    def reported_message_body(self, obj):
        from django.utils.html import format_html
        text = self._reported_text(obj)
        if text:
            return format_html(
                '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 14px;'
                'max-width:600px;white-space:pre-wrap;font-size:13px;">{}</div>',
                text,
            )
        return format_html(
            '<em style="color:#9ca3af;">No message or content was linked to this report. '
            'The reporter described the concern in the description below.</em>'
        )
    reported_message_body.short_description = 'Reported content'

    @admin.action(description='Mark selected as Under Review')
    def mark_under_review(self, request, queryset):
        updated = queryset.exclude(status=AbuseReport.Status.RESOLVED).update(
            status=AbuseReport.Status.UNDER_REVIEW
        )
        self.message_user(request, f'{updated} report(s) marked as under review.')

    @admin.action(description='Mark selected as Resolved')
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for report in queryset.exclude(status=AbuseReport.Status.RESOLVED):
            report.status = AbuseReport.Status.RESOLVED
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.save(update_fields=['status', 'resolved_by', 'resolved_at'])
            updated += 1
        self.message_user(request, f'{updated} report(s) marked as resolved.')
