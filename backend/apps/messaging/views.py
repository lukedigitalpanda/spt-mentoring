import csv
from django.db.models import Max, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import HttpResponse
from django.utils import timezone
from .models import Conversation, Message, MessageRead, MassMessage, AbuseReport
from .serializers import (
    ConversationSerializer, MessageSerializer, MassMessageSerializer, AbuseReportSerializer
)
from apps.moderation.service import ModerationService


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['subject', 'participants__first_name', 'participants__last_name']

    def get_queryset(self):
        user = self.request.user
        qs = Conversation.objects.prefetch_related('participants', 'messages')
        if not (user.role == 'admin' or user.is_staff):
            # TC-08: exclude conversations that have any inactive participant — deactivated
            # accounts should not appear in the sidebar preview of the active user.
            # .distinct() is required because exclude() across a M2M can produce duplicates.
            qs = (
                qs.filter(participants=user)
                .exclude(participants__is_active=False)
                .distinct()
            )
        # Order by most recent message first so mass messages and active threads surface at top.
        return qs.annotate(last_msg_at=Max('messages__sent_at')).order_by('-last_msg_at')

    def perform_create(self, serializer):
        # MSG-05 guard: non-admin users may only open conversations with users
        # they hold an ACTIVE mentoring match with (admins/staff participants
        # are exempt so support threads still work). Support and sponsor
        # conversations are created via the dedicated actions below, which
        # build the conversation server-side and never hit this path.
        from rest_framework.exceptions import PermissionDenied
        user = self.request.user
        if not (user.is_staff or user.role == 'admin'):
            from apps.users.models import MentoringMatch
            from django.db.models import Q
            others = [p for p in serializer.validated_data.get('participants', []) if p.pk != user.pk]
            for other in others:
                if other.is_staff or other.role == 'admin':
                    continue
                has_active_match = MentoringMatch.objects.filter(
                    Q(scholar=user, mentor=other) | Q(scholar=other, mentor=user),
                    is_active=True,
                ).exists()
                if not has_active_match:
                    raise PermissionDenied(
                        'You can only start conversations with users you are actively matched with.'
                    )
        conv = serializer.save()
        conv.participants.add(self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def contact_support(self, request):
        """Get or create a direct support conversation with the Arkwright admin account.
        Scholars only — opens an existing conversation if one already exists."""
        from apps.users.models import User
        from apps.notifications.models import Notification

        if not any(r in request.user.all_roles for r in ('scholar', 'mentor', 'sponsor')):
            return Response({'error': 'Only scholars, mentors, and sponsors can contact support.'}, status=status.HTTP_403_FORBIDDEN)

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

        # Return existing conversation if one already exists
        existing = (
            Conversation.objects
            .filter(participants=request.user)
            .filter(participants=arkwright)
            .filter(conversation_type=Conversation.ConversationType.DIRECT)
            .first()
        )
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data)

        conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.DIRECT,
            subject='Support',
            support_status=Conversation.SupportStatus.OPEN,
        )
        conv.participants.add(arkwright, request.user)

        # Notify all active admins (excluding arkwright itself)
        admin_users = User.objects.filter(is_active=True, role='admin').exclude(pk=arkwright.pk)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                notification_type=Notification.Type.MESSAGE,
                title=f'Support request from {request.user.full_name}',
                body=f'{request.user.full_name} has started a support conversation.',
                link='/messages',
            )

        serializer = self.get_serializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def contact_sponsor(self, request):
        """Get or create a sponsor-update conversation between a scholar and their sponsor.
        Scholars initiate; sponsors can also call this with ?scholar_id= to open a conversation
        with a specific linked scholar."""
        from apps.users.models import User

        user = request.user

        if 'scholar' in user.all_roles:
            # Scholar opens/gets conversation with their sponsor
            try:
                sponsor_user = user.scholar_profile.sponsor
            except Exception:
                sponsor_user = None
            if not sponsor_user:
                return Response(
                    {'error': 'You do not have a sponsor linked to your profile. Please contact an administrator.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            other_user = sponsor_user

        elif 'sponsor' in user.all_roles:
            # Sponsor opens/gets conversation with a specific scholar.
            # ISS-H: accept scholars whose primary OR secondary role is scholar.
            scholar_id = request.data.get('scholar_id')
            if not scholar_id:
                return Response({'error': 'scholar_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                scholar = User.objects.get(
                    pk=scholar_id,
                    scholar_profile__sponsor=user,
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Scholar not found or not linked to your account.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            other_user = scholar

        else:
            return Response(
                {'error': 'Only scholars and sponsors can use this endpoint.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Return existing conversation if one already exists between the pair
        existing = (
            Conversation.objects
            .filter(participants=user)
            .filter(participants=other_user)
            .filter(conversation_type=Conversation.ConversationType.SPONSOR_UPDATE)
            .first()
        )
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data)

        conv = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.SPONSOR_UPDATE,
            subject='Sponsor Update',
        )
        conv.participants.add(user, other_user)
        serializer = self.get_serializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def export(self, request):
        """Export all messages as CSV for admin review."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="messages_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Conversation ID', 'Subject', 'Type', 'Sender', 'Body', 'Status', 'Participants'])

        messages = (
            Message.objects
            .select_related('sender', 'conversation')
            .prefetch_related('conversation__participants')
            .exclude(status=Message.Status.DELETED)
            .order_by('-sent_at')
        )
        date_from = request.query_params.get('date_from')
        date_to   = request.query_params.get('date_to')
        if date_from:
            messages = messages.filter(sent_at__date__gte=date_from)
        if date_to:
            messages = messages.filter(sent_at__date__lte=date_to)

        for msg in messages:
            participants = ', '.join(p.full_name for p in msg.conversation.participants.all())
            writer.writerow([
                msg.sent_at.strftime('%Y-%m-%d %H:%M'),
                msg.conversation_id,
                msg.conversation.subject or '',
                msg.conversation.conversation_type,
                msg.sender.full_name,
                msg.body,
                msg.status,
                participants,
            ])
        return response


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['sent_at']

    def get_queryset(self):
        user = self.request.user
        qs = Message.objects.select_related('sender').filter(
            conversation__participants=user
        )
        if not (user.is_staff or user.role == 'admin'):
            # Non-staff see every DELIVERED message in the conversation, plus
            # their own held/blocked messages (P2-1a), but never another
            # participant's held/blocked content. Recipient privacy is the
            # invariant that must never break here.
            qs = qs.filter(
                Q(status=Message.Status.DELIVERED)
                | Q(sender=user, status__in=[Message.Status.FLAGGED, Message.Status.BLOCKED])
            )
        conv_id = self.request.query_params.get('conversation')
        if conv_id:
            qs = qs.filter(conversation_id=conv_id)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Auto-mark all fetched messages in this conversation as read
        conv_id = request.query_params.get('conversation')
        if conv_id:
            unread = Message.objects.filter(
                conversation_id=conv_id,
                status=Message.Status.DELIVERED,
            ).exclude(reads__user=request.user)
            for msg in unread:
                MessageRead.objects.get_or_create(message=msg, user=request.user)
            # Also mark related notifications as read
            from apps.notifications.models import Notification
            Notification.objects.filter(
                user=request.user,
                notification_type=Notification.Type.MESSAGE,
                is_read=False,
                link='/messages',
            ).update(is_read=True)
        return response

    def create(self, request, *args, **kwargs):
        """
        Override create() so we can return a distinct HTTP status code and
        human-readable detail message for each moderation outcome.

        Also enforces that all conversation participants are active — inactive
        users cannot send or receive messages.


          201 Created   – message passed screening and was delivered
          202 Accepted  – message matched a FlaggedTerm; held for admin review
          400 Bad Request – message matched a BlockedTerm; permanently rejected

        The message record is persisted in all cases so admins can audit it.
        """
        # Block messaging if the sender is inactive
        if not request.user.is_active:
            return Response(
                {'detail': 'Your account is inactive. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Block messaging if any other participant in the conversation is inactive
        conv_id = request.data.get('conversation')
        if conv_id:
            inactive_participants = (
                Conversation.objects
                .filter(pk=conv_id, participants__is_active=False)
                .exclude(participants=request.user)
                .exists()
            )
            if inactive_participants:
                return Response(
                    {'detail': 'This conversation includes an inactive participant and cannot receive new messages.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Block messaging if the sender and recipient have a mentoring
            # relationship but all matches between them are inactive (unmatched).
            # This covers both Task 1 (unmatch) and Task 2 (old match after re-link).
            try:
                conv = Conversation.objects.get(pk=conv_id)
            except Conversation.DoesNotExist:
                conv = None
            if conv and conv.conversation_type == Conversation.ConversationType.DIRECT:
                from apps.users.models import MentoringMatch
                from django.db.models import Q
                other_participants = list(conv.participants.exclude(pk=request.user.pk))
                for other in other_participants:
                    match_qs = MentoringMatch.objects.filter(
                        Q(scholar=request.user, mentor=other) |
                        Q(scholar=other, mentor=request.user)
                    )
                    if match_qs.exists() and not match_qs.filter(is_active=True).exists():
                        return Response(
                            {'detail': 'You cannot send messages as your mentoring relationship is no longer active.'},
                            status=status.HTTP_403_FORBIDDEN,
                        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        result = ModerationService.screen(message)
        MessageRead.objects.create(message=message, user=request.user)

        if result.status == 'blocked':
            reason = ModerationService.sender_facing_reason(result)
            return Response(
                {
                    'detail': (
                        f'Your message could not be sent because {reason}. '
                        'Please edit it and try again.'
                    ),
                    'moderation_status': 'blocked',
                    'moderation_reason': reason,
                    'message': self.get_serializer(message).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result.status == 'flagged':
            reason = ModerationService.sender_facing_reason(result)
            return Response(
                {
                    'detail': (
                        f'Your message has been held for review before delivery because {reason}. '
                        'A moderator will review it shortly and you will be notified of the outcome. '
                        'You can edit the message to remove the highlighted issue and resend it.'
                    ),
                    'moderation_status': 'pending_review',
                    'moderation_reason': reason,
                    'message': self.get_serializer(message).data,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Mirror the WebSocket consumer: broadcast delivered messages to the
        # conversation group so recipients with the thread open see REST-created
        # messages (attachments, socket-fallback sends) live. Never let a
        # broadcast failure break the send itself.
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{message.conversation_id}',
                    {
                        'type': 'chat_message',
                        'message_id': message.pk,
                        'body': message.body,
                        'sender_id': request.user.pk,
                        'sender_name': request.user.full_name,
                        'sent_at': message.sent_at.isoformat(),
                        'attachment_url': message.attachment.url if message.attachment else None,
                        'attachment_name': message.attachment_name or (message.body if message.attachment else ''),
                    },
                )
        except Exception:
            import logging
            logging.getLogger('apps.messaging').exception(
                'Failed to broadcast REST-created message #%d', message.pk
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        MessageRead.objects.get_or_create(message=message, user=request.user)
        return Response({'status': 'read'})


class MassMessageViewSet(viewsets.ModelViewSet):
    """Admin-only broadcast messaging."""
    queryset = MassMessage.objects.all().order_by('-sent_at')
    serializer_class = MassMessageSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Queue a mass message for background delivery.

        The fan-out (one conversation + message + notification + email per
        recipient) runs in a Celery worker so the request returns immediately
        and never hits the nginx gateway timeout (MSG-06).
        """
        mass_msg = self.get_object()
        if mass_msg.status in (MassMessage.Status.SENDING, MassMessage.Status.SENT):
            return Response(
                {'error': 'This message has already been sent or is currently sending.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .tasks import send_mass_message_task
        mass_msg.status = MassMessage.Status.SENDING
        mass_msg.save(update_fields=['status'])
        send_mass_message_task.delay(mass_msg.pk)
        return Response({'status': 'sending'}, status=status.HTTP_202_ACCEPTED)


class AbuseReportViewSet(viewsets.ModelViewSet):
    serializer_class = AbuseReportSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return AbuseReport.objects.all().order_by('-created_at')
        return AbuseReport.objects.filter(reporter=user)

    def perform_create(self, serializer):
        report = serializer.save(reporter=self.request.user)
        # Snapshot the reported message body so the report detail always shows
        # what was reported, even if the message is later deleted (P2-6).
        if report.message and not report.reported_content:
            report.reported_content = report.message.body
            report.save(update_fields=['reported_content'])
        # Notify all active admins of the new safeguarding report
        from apps.users.models import User
        from apps.notifications.models import Notification
        admin_users = User.objects.filter(is_active=True, role='admin')
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                notification_type=Notification.Type.SYSTEM,
                title='New safeguarding report filed',
                body=f'{self.request.user.full_name} submitted an abuse report: {report.description[:100]}',
                link='/admin/messaging/abusereport/',
            )

    def destroy(self, request, *args, **kwargs):
        """Abuse reports must never be deleted — use the resolve action to close them."""
        return Response(
            {'error': 'Abuse reports cannot be deleted. Use the resolve action to close a report.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def resolve(self, request, pk=None):
        report = self.get_object()
        report.status = AbuseReport.Status.RESOLVED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_notes = request.data.get('notes', '')
        report.save()
        return Response({'status': 'resolved'})
