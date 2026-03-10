from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .models import BlockedTerm, FlaggedTerm, ModerationLog
from .serializers import BlockedTermSerializer, FlaggedTermSerializer, ModerationLogSerializer
from apps.moderation.service import ModerationService


class BlockedTermViewSet(viewsets.ModelViewSet):
    queryset = BlockedTerm.objects.all().order_by('term')
    serializer_class = BlockedTermSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class FlaggedTermViewSet(viewsets.ModelViewSet):
    queryset = FlaggedTerm.objects.all().order_by('-severity', 'term')
    serializer_class = FlaggedTermSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class ModerationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModerationLog.objects.select_related('message', 'actioned_by').all()
    serializer_class = ModerationLogSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['action']


class FlaggedMessageViewSet(viewsets.ViewSet):
    """Review queue for flagged messages awaiting admin decision."""
    permission_classes = [IsAdminUser]

    def list(self, request):
        from apps.messaging.models import Message
        from apps.messaging.serializers import MessageSerializer
        flagged = Message.objects.filter(status=Message.Status.FLAGGED).select_related('sender')
        return Response(MessageSerializer(flagged, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from apps.messaging.models import Message
        try:
            msg = Message.objects.get(pk=pk, status=Message.Status.FLAGGED)
        except Message.DoesNotExist:
            return Response({'error': 'Not found or not flagged'}, status=status.HTTP_404_NOT_FOUND)
        ModerationService.approve(msg, request.user, notes=request.data.get('notes', ''))
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        from apps.messaging.models import Message
        try:
            msg = Message.objects.get(pk=pk, status=Message.Status.FLAGGED)
        except Message.DoesNotExist:
            return Response({'error': 'Not found or not flagged'}, status=status.HTTP_404_NOT_FOUND)
        ModerationService.reject(msg, request.user, notes=request.data.get('notes', ''))
        return Response({'status': 'rejected'})
