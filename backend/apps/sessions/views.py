from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import AvailabilitySlot, MentoringSession, SessionFeedback
from .serializers import (
    AvailabilitySlotSerializer,
    MentoringSessionSerializer,
    SessionFeedbackSerializer,
)


def _notify(user, notification_type, title, body, link=''):
    """Helper to create an in-app notification without circular imports."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            link=link,
        )
    except Exception:
        pass


class AvailabilitySlotViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilitySlotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['mentor', 'is_booked']
    ordering_fields = ['start_time']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return AvailabilitySlot.objects.select_related('mentor').all()
        if user.role == 'mentor':
            return AvailabilitySlot.objects.filter(mentor=user)
        # Scholars/sponsors see all future, unbooked slots
        return AvailabilitySlot.objects.filter(
            is_booked=False,
            start_time__gt=timezone.now(),
        ).select_related('mentor')

    def perform_create(self, serializer):
        # Mentors can only create their own slots
        user = self.request.user
        if user.role == 'mentor':
            serializer.save(mentor=user)
        else:
            serializer.save()

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated()]
        return [IsAuthenticated()]


class MentoringSessionViewSet(viewsets.ModelViewSet):
    serializer_class = MentoringSessionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'mentor', 'scholar']
    search_fields = ['title', 'agenda']
    ordering_fields = ['start_time', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return MentoringSession.objects.select_related('mentor', 'scholar').prefetch_related('feedback').all()
        return MentoringSession.objects.filter(
            mentor=user
        ).union(
            MentoringSession.objects.filter(scholar=user)
        ).order_by('-start_time')

    def perform_create(self, serializer):
        session = serializer.save(created_by=self.request.user)
        # Mark slot as booked
        if session.slot:
            session.slot.is_booked = True
            session.slot.save(update_fields=['is_booked'])
        # Notify mentor of new request
        _notify(
            session.mentor,
            'session_request',
            'New session request',
            f"{session.scholar.full_name} has requested a session on "
            f"{session.start_time.strftime('%d %b %Y at %H:%M')}",
            '/sessions',
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if user != session.mentor and not (user.is_staff or user.role == 'admin'):
            return Response({'error': 'Only the mentor can confirm.'}, status=status.HTTP_403_FORBIDDEN)
        session.status = MentoringSession.Status.CONFIRMED
        session.save(update_fields=['status'])
        _notify(
            session.scholar,
            'session_confirmed',
            'Session confirmed!',
            f"Your session with {session.mentor.full_name} on "
            f"{session.start_time.strftime('%d %b at %H:%M')} is confirmed.",
            '/sessions',
        )
        return Response(MentoringSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if user not in (session.mentor, session.scholar) and not (user.is_staff or user.role == 'admin'):
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        session.status = MentoringSession.Status.CANCELLED
        session.save(update_fields=['status'])
        # Free up slot
        if session.slot:
            session.slot.is_booked = False
            session.slot.save(update_fields=['is_booked'])
        # Notify the other party
        other = session.scholar if user == session.mentor else session.mentor
        _notify(
            other,
            'session_cancelled',
            'Session cancelled',
            f"The session on {session.start_time.strftime('%d %b at %H:%M')} has been cancelled.",
            '/sessions',
        )
        return Response(MentoringSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if not (user.is_staff or user.role == 'admin' or user == session.mentor):
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        session.status = MentoringSession.Status.COMPLETED
        session.save(update_fields=['status'])
        # Notify both parties to submit feedback
        for recipient in (session.mentor, session.scholar):
            _notify(
                recipient,
                'session_feedback',
                'How was your session?',
                f"Please rate your session with "
                f"{'your scholar' if recipient == session.mentor else 'your mentor'}.",
                f'/sessions/{session.pk}',
            )
        return Response(MentoringSessionSerializer(session).data)


class SessionFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = SessionFeedbackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return SessionFeedback.objects.select_related('from_user', 'session').all()
        return SessionFeedback.objects.filter(
            session__mentor=user
        ).union(
            SessionFeedback.objects.filter(session__scholar=user)
        )

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)
