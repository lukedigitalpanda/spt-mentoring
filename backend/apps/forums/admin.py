from django.contrib import admin
from django.utils.html import format_html
from .models import Forum, Thread, Post


class FormFixMixin:
    """Injects form_fix.css as the very last stylesheet on change pages."""
    class Media:
        css = {'all': ('admin/css/form_fix.css',)}


class ThreadInline(admin.TabularInline):
    model = Thread
    extra = 0
    fields = ['title', 'is_pinned', 'is_locked', 'created_by', 'created_at']
    readonly_fields = ['created_by', 'created_at']
    show_change_link = True


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ['title', 'visibility', 'programme', 'is_active', 'thread_count', 'created_at']
    list_filter = ['visibility', 'is_active', 'programme']
    search_fields = ['title', 'description']
    filter_horizontal = ['members']
    readonly_fields = ['created_at', 'created_by']
    inlines = [ThreadInline]
    fieldsets = (
        (None, {'fields': ('title', 'description', 'is_active')}),
        ('Access', {'fields': ('visibility', 'programme', 'members', 'notify_all_members')}),
        ('Metadata', {'fields': ('created_by', 'created_at')}),
    )

    def thread_count(self, obj):
        return obj.threads.count()
    thread_count.short_description = 'Threads'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    fields = ['author', 'body', 'status', 'created_at']
    readonly_fields = ['author', 'created_at']
    show_change_link = True


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'forum', 'created_by', 'is_pinned', 'is_locked', 'post_count', 'created_at']
    list_filter = ['is_pinned', 'is_locked', 'forum']
    search_fields = ['title', 'forum__title']
    readonly_fields = ['created_at', 'created_by']
    inlines = [PostInline]

    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'


@admin.register(Post)
class PostAdmin(FormFixMixin, admin.ModelAdmin):
    list_display = ['author', 'thread', 'body_preview', 'status', 'moderation_note', 'created_at', 'moderation_actions']
    list_filter = ['status', 'thread__forum']
    search_fields = ['body', 'author__email', 'thread__title']
    readonly_fields = ['author', 'created_at', 'updated_at', 'moderated_by', 'moderated_at', 'message_author_panel']
    fields = ['thread', 'author', 'body', 'status', 'moderation_note', 'moderated_by', 'moderated_at',
              'attachment', 'created_at', 'updated_at', 'message_author_panel']
    actions = ['approve_posts', 'reject_posts']

    def body_preview(self, obj):
        return obj.body[:80] + ('…' if len(obj.body) > 80 else '')
    body_preview.short_description = 'Post'

    def save_model(self, request, obj, form, change):
        """Auto-populate moderation audit fields when status is changed manually."""
        if change and 'status' in form.changed_data:
            from django.utils import timezone
            obj.moderated_by = request.user
            obj.moderated_at = timezone.now()
        super().save_model(request, obj, form, change)

    def message_author_panel(self, obj):
        """Allow admin to message the post author directly from the moderation view."""
        if not obj.pk or not obj.author_id:
            return '—'
        from django.urls import reverse
        msg_url = reverse('admin:forums_post_message_author', args=[obj.pk])
        pk = obj.pk
        return format_html(
            '<div>'
            '<p style="font-size:0.8rem;color:#555;margin:0 0 6px;">'
            'Send a message to <strong>{author}</strong> as Arkwright support:</p>'
            '<textarea id="fpost-body-{pk}" rows="3" placeholder="Type your message here…" '
            'style="width:100%;max-width:520px;border:1px solid #d1c4e9;border-radius:8px;'
            'padding:8px 10px;font-size:0.82rem;resize:vertical;"></textarea><br>'
            '<button type="button" id="fpost-btn-{pk}" data-url="{url}" '
            'style="margin-top:8px;background:#7c3aed;color:#fff;'
            'padding:6px 18px;border-radius:6px;font-weight:700;border:none;cursor:pointer;">'
            '✉ Message {author}</button>'
            '<span id="fpost-status-{pk}" style="margin-left:10px;font-size:0.82rem;"></span>'
            '</div>'
            '<script>(function(){{'
            'var btn=document.getElementById("fpost-btn-{pk}");'
            'btn.addEventListener("click",function(){{'
            'var body=document.getElementById("fpost-body-{pk}").value.trim();'
            'if(!body){{alert("Please enter a message.");return;}}'
            'var csrf="",m=document.cookie.match(/csrftoken=([^;]+)/);'
            'if(m)csrf=decodeURIComponent(m[1]);'
            'btn.disabled=true;'
            'var st=document.getElementById("fpost-status-{pk}");'
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
            'document.getElementById("fpost-body-{pk}").value="";'
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
            url=msg_url,
            author=obj.author.full_name if obj.author else '—',
        )
    message_author_panel.short_description = 'Message author'

    # ── Moderation queue helpers ──────────────────────────────────────────────

    def _redirect_to_queue(self, request, exclude_pks=()):
        """Redirect to the next FLAGGED post, or the filtered list if none remain."""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        next_post = (
            Post.objects.filter(status=Post.Status.FLAGGED)
            .exclude(pk__in=exclude_pks)
            .order_by('created_at')
            .first()
        )
        if next_post:
            self.message_user(
                request,
                f'Next flagged post from {next_post.author} is ready for review.',
            )
            return HttpResponseRedirect(
                reverse('admin:forums_post_change', args=[next_post.pk])
            )
        return HttpResponseRedirect(
            reverse('admin:forums_post_changelist') + '?status__exact=flagged'
        )

    def moderation_actions(self, obj):
        """Inline approve / reject buttons shown on the list view."""
        if obj.status not in (Post.Status.FLAGGED, Post.Status.PENDING):
            return format_html('<span style="color:#bbb;">—</span>')
        from django.urls import reverse
        approve_url = reverse('admin:forums_post_quick_moderate', args=[obj.pk, 'approve'])
        reject_url = reverse('admin:forums_post_quick_moderate', args=[obj.pk, 'reject'])
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
    moderation_actions.short_description = 'Quick action'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        return [
            path(
                '<int:pk>/message-author/',
                self.admin_site.admin_view(self.message_author_view),
                name='forums_post_message_author',
            ),
            path(
                '<int:pk>/moderate/<str:action>/',
                self.admin_site.admin_view(self.quick_moderate_view),
                name='forums_post_quick_moderate',
            ),
        ] + urls

    def message_author_view(self, request, pk):
        """Send a direct message to the post author as Arkwright."""
        from django.http import JsonResponse
        from apps.users.models import User
        from apps.messaging.models import Conversation, Message, MessageRead

        if request.method != 'POST':
            return JsonResponse({'error': 'POST required.'}, status=405)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        body = request.POST.get('body', '').strip()
        if not body:
            return JsonResponse({'error': 'Message body cannot be empty.'}, status=400)

        try:
            post = Post.objects.select_related('author').get(pk=pk)
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found.'}, status=404)

        arkwright, _ = User.objects.get_or_create(
            email='arkwright@spt.org',
            defaults={
                'username': 'arkwright', 'first_name': 'Arkwright', 'last_name': '',
                'role': 'admin', 'is_active': True, 'notification_email': False, 'is_verified': True,
            },
        )

        # Find or create a support conversation with the author
        conv = (
            Conversation.objects
            .filter(participants=post.author)
            .filter(participants=arkwright)
            .filter(conversation_type=Conversation.ConversationType.DIRECT)
            .first()
        )
        if not conv:
            conv = Conversation.objects.create(
                conversation_type=Conversation.ConversationType.DIRECT,
                subject='Support',
            )
            conv.participants.add(arkwright, post.author)

        msg = Message.objects.create(
            conversation=conv,
            sender=arkwright,
            body=body,
            status=Message.Status.DELIVERED,
        )
        MessageRead.objects.create(message=msg, user=arkwright)

        if is_ajax:
            return JsonResponse({'status': 'ok'})
        from django.shortcuts import redirect
        from django.urls import reverse
        self.message_user(request, f'Message sent to {post.author.full_name}.')
        return redirect(reverse('admin:forums_post_change', args=[pk]))

    def quick_moderate_view(self, request, pk, action):
        """Single-click approve or reject from the list-view inline buttons."""
        from django.utils import timezone
        try:
            post = Post.objects.select_related('author').get(pk=pk)
        except Post.DoesNotExist:
            self.message_user(request, f'Post #{pk} not found.', level='ERROR')
            return self._redirect_to_queue(request)

        if action == 'approve' and post.status in (Post.Status.FLAGGED, Post.Status.PENDING):
            post.status = Post.Status.VISIBLE
            post.moderated_by = request.user
            post.moderated_at = timezone.now()
            post.save(update_fields=['status', 'moderated_by', 'moderated_at'])
            self.message_user(request, f'Post by {post.author.full_name} approved and now visible.')
        elif action == 'reject' and post.status in (
            Post.Status.FLAGGED, Post.Status.PENDING, Post.Status.VISIBLE
        ):
            post.status = Post.Status.HIDDEN
            post.moderated_by = request.user
            post.moderated_at = timezone.now()
            post.save(update_fields=['status', 'moderated_by', 'moderated_at'])
            self.message_user(request, f'Post by {post.author.full_name} rejected and hidden.')
        else:
            self.message_user(
                request,
                f'No action taken — post #{pk} is already {post.get_status_display()}.',
                level='WARNING',
            )

        return self._redirect_to_queue(request, exclude_pks=[pk])

    def response_change(self, request, obj):
        """After saving a post detail, return to the moderation queue."""
        if '_save' in request.POST:
            return self._redirect_to_queue(request, exclude_pks=[obj.pk])
        return super().response_change(request, obj)

    @admin.action(description='✅ Approve selected posts (make visible)')
    def approve_posts(self, request, queryset):
        from django.utils import timezone
        updated = 0
        actioned_ids = list(queryset.values_list('pk', flat=True))
        for post in queryset.filter(status__in=[Post.Status.FLAGGED, Post.Status.PENDING]):
            post.status = Post.Status.VISIBLE
            post.moderated_by = request.user
            post.moderated_at = timezone.now()
            post.save(update_fields=['status', 'moderated_by', 'moderated_at'])
            updated += 1
        skipped = queryset.count() - updated
        msg = f'{updated} post(s) approved and now visible.'
        if skipped:
            msg += f' {skipped} skipped (already visible or hidden).'
        self.message_user(request, msg)
        return self._redirect_to_queue(request, exclude_pks=actioned_ids)

    @admin.action(description='❌ Reject selected posts (hide permanently)')
    def reject_posts(self, request, queryset):
        from django.utils import timezone
        updated = 0
        actioned_ids = list(queryset.values_list('pk', flat=True))
        for post in queryset.filter(status__in=[Post.Status.FLAGGED, Post.Status.PENDING, Post.Status.VISIBLE]):
            post.status = Post.Status.HIDDEN
            post.moderated_by = request.user
            post.moderated_at = timezone.now()
            post.save(update_fields=['status', 'moderated_by', 'moderated_at'])
            updated += 1
        self.message_user(request, f'{updated} post(s) hidden.')
        return self._redirect_to_queue(request, exclude_pks=actioned_ids)
