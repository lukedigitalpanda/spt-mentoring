import csv
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
        if user.role == 'admin' or user.is_staff:
            return Conversation.objects.prefetch_related('participants', 'messages').all()
        return Conversation.objects.prefetch_related('participants', 'messages').filter(participants=user)

    def perform_create(self, serializer):
        conv = serializer.save()
        conv.participants.add(self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def contact_support(self, request):
        """Get or create a direct support conversation with the Arkwright admin account.
        Scholars only — opens an existing conversation if one already exists."""
        from apps.users.models import User
        from apps.notifications.models import Notification

        if request.user.role != 'scholar':
            return Response({'error': 'Only scholars can contact support.'}, status=status.HTTP_403_FORBIDDEN)

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
            qs = qs.filter(status=Message.Status.DELIVERED)
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

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        message = serializer.save(sender=self.request.user)
        # Run moderation pipeline
        result = ModerationService.screen(message)
        # Mark as read by sender immediately
        MessageRead.objects.create(message=message, user=self.request.user)
        # Tell the sender if their message was blocked
        if result.status == 'blocked':
            raise PermissionDenied(
                'Your message could not be sent as it contains content that is not permitted on this platform.'
            )

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
        """Send a mass message and create in-app conversations for each recipient."""
        mass_msg = self.get_object()
        if mass_msg.status == MassMessage.Status.SENT:
            return Response({'error': 'Already sent'}, status=status.HTTP_400_BAD_REQUEST)
        from .tasks import send_mass_message_task
        # Run synchronously so we can return the recipient count immediately
        send_mass_message_task(mass_msg.pk)
        mass_msg.refresh_from_db()
        return Response({'status': 'sent', 'recipient_count': mass_msg.recipient_count})


class AbuseReportViewSet(viewsets.ModelViewSet):
    serializer_class = AbuseReportSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return AbuseReport.objects.all().order_by('-created_at')
        return AbuseReport.objects.filter(reporter=user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def resolve(self, request, pk=None):
        report = self.get_object()
        report.status = AbuseReport.Status.RESOLVED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_notes = request.data.get('notes', '')
        report.save()
        return Response({'status': 'resolved'})
