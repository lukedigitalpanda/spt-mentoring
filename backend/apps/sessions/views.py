from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
        with transaction.atomic():
            if user.role == 'mentor':
                slot = serializer.save(mentor=user)
            else:
                slot = serializer.save()
            self._merge_overlapping(slot)

    def _merge_overlapping(self, slot):
        """Absorb any same-mentor, unbooked slots that overlap or touch the
        new slot into a single slot spanning the full extent. Booked slots
        are never touched."""
        overlapping = AvailabilitySlot.objects.filter(
            mentor=slot.mentor, is_booked=False,
            start_time__lte=slot.end_time, end_time__gte=slot.start_time,
        ).exclude(id=slot.id)
        if overlapping.exists():
            slot.start_time = min([slot.start_time] + [s.start_time for s in overlapping])
            slot.end_time = max([slot.end_time] + [s.end_time for s in overlapping])
            slot.save(update_fields=['start_time', 'end_time'])
            overlapping.delete()

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
        from django.db.models import Q
        return MentoringSession.objects.filter(
            Q(mentor=user) | Q(scholar=user)
        ).select_related('mentor', 'scholar').prefetch_related('feedback').order_by('-start_time')

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

    @action(detail=False, methods=['post'])
    def propose(self, request):
        """Mentor proposes a session at a specific date/time for a scholar
        they are actively matched with. Creates the AvailabilitySlot
        directly (never via AvailabilitySlotViewSet.perform_create) so it
        is booked from the outset and can never be absorbed by, or absorb,
        another slot in the merge pass."""
        user = request.user
        if user.role != 'mentor':
            return Response({'error': 'Only mentors can propose a session.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.users.models import MentoringMatch, User as UserModel
        scholar_id = request.data.get('scholar')
        try:
            scholar = UserModel.objects.get(pk=scholar_id)
        except (UserModel.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Scholar not found.'}, status=status.HTTP_400_BAD_REQUEST)

        matched = MentoringMatch.objects.filter(mentor=user, scholar=scholar, is_active=True).exists()
        if not matched:
            return Response(
                {'error': 'You are not actively matched with this scholar.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        start_time = parse_datetime(str(request.data.get('start_time') or ''))
        end_time = parse_datetime(str(request.data.get('end_time') or ''))
        if not start_time or not end_time:
            return Response(
                {'error': 'start_time and end_time are required and must be valid datetimes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)

        if start_time >= end_time:
            return Response({'error': 'start_time must be before end_time.'}, status=status.HTTP_400_BAD_REQUEST)
        if start_time <= timezone.now():
            return Response({'error': 'start_time must be in the future.'}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title') or 'Mentoring Session'
        agenda = request.data.get('agenda', '')

        with transaction.atomic():
            slot = AvailabilitySlot.objects.create(
                mentor=user, start_time=start_time, end_time=end_time, is_booked=True,
            )
            session = MentoringSession.objects.create(
                mentor=user, scholar=scholar, slot=slot,
                title=title, start_time=start_time, end_time=end_time,
                agenda=agenda, status=MentoringSession.Status.PENDING,
                created_by=user,
            )

        _notify(
            scholar,
            'session_request',
            'Session proposed',
            'Your mentor has proposed a session - review and confirm.',
            '/sessions',
        )
        return Response(MentoringSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if session.status != MentoringSession.Status.PENDING:
            return Response(
                {'error': 'Only pending sessions can be confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_staff = user.is_staff or user.role == 'admin'
        if not is_staff:
            if session.created_by_id is None:
                # Legacy sessions predating creator tracking: mentor confirms.
                if user != session.mentor:
                    return Response({'error': 'Only the mentor can confirm.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                if user not in (session.mentor, session.scholar):
                    return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
                if user == session.created_by:
                    return Response(
                        {'error': 'You cannot confirm a session you proposed. Waiting for the other party.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
        session.status = MentoringSession.Status.CONFIRMED
        session.save(update_fields=['status'])
        # Notify whichever participant did not just confirm it (defaulting
        # to notifying the scholar, as before, when staff confirm on
        # someone's behalf).
        recipient = session.mentor if user == session.scholar else session.scholar
        partner_name = session.scholar.full_name if recipient == session.mentor else session.mentor.full_name
        _notify(
            recipient,
            'session_confirmed',
            'Session confirmed!',
            f"Your session with {partner_name} on "
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

    @action(detail=True, methods=['get'])
    def join(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if user not in (session.mentor, session.scholar) and not (user.is_staff or user.role == 'admin'):
            return Response({'error': 'Not authorised.'}, status=status.HTTP_403_FORBIDDEN)
        if not session.is_joinable:
            return Response(
                {'error': 'This session is not open to join right now.'},
                status=status.HTTP_409_CONFLICT,
            )
        from .jaas import build_join_url, is_configured
        url = build_join_url(session, user) if is_configured() else session.meeting_url
        return Response({'url': url})


class SessionFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = SessionFeedbackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return SessionFeedback.objects.select_related('from_user', 'session').all()
        from django.db.models import Q
        return SessionFeedback.objects.filter(
            Q(session__mentor=user) | Q(session__scholar=user)
        ).select_related('from_user', 'session')

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)
