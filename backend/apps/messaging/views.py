from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
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

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        # Run moderation pipeline
        ModerationService.screen(message)
        # Mark as read by sender immediately
        MessageRead.objects.create(message=message, user=self.request.user)

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
        """Trigger async send of a draft mass message."""
        mass_msg = self.get_object()
        if mass_msg.status == MassMessage.Status.SENT:
            return Response({'error': 'Already sent'}, status=status.HTTP_400_BAD_REQUEST)
        from .tasks import send_mass_message_task
        send_mass_message_task.delay(mass_msg.pk)
        return Response({'status': 'queued'})


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
