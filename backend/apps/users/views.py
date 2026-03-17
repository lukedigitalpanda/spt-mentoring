from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import User, MentoringMatch, MentorWaitingList
from .serializers import (
    UserSerializer, UserListSerializer, UserCreateSerializer,
    MentoringMatchSerializer, MentorWaitingListSerializer,
)
from .filters import UserFilter
from .permissions import IsAdminOrSelf


class UserViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for users. Admins can manage all users; others can only view/edit themselves.
    Supports full-text search across name, email, location, engineering discipline.
    """
    queryset = User.objects.select_related('mentor_profile', 'scholar_profile', 'sponsor_profile').order_by('last_name', 'first_name')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['first_name', 'last_name', 'email', 'location', 'engineering_discipline', 'crm_id']
    ordering_fields = ['last_name', 'email', 'role', 'date_joined']

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ('create', 'destroy', 'bulk_upload'):
            return [IsAdminUser()]
        if self.action in ('retrieve', 'update', 'partial_update'):
            return [IsAdminOrSelf()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Return or update the currently authenticated user."""
        if request.method == 'PATCH':
            serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(UserSerializer(request.user, context={'request': request}).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='me/data-export')
    def my_data_export(self, request):
        """GDPR Article 20 — return all personal data held about the authenticated user as JSON."""
        from apps.messaging.models import Message
        from apps.sessions.models import MentoringSession
        user = request.user

        messages = Message.objects.filter(
            sender=user, status=Message.Status.DELIVERED
        ).values('body', 'sent_at', 'conversation_id')

        sessions = MentoringSession.objects.filter(
            scholar=user
        ).values('status', 'scheduled_at', 'notes') if hasattr(user, 'scholar_sessions') else []

        data = {
            'exported_at': timezone.now().isoformat(),
            'profile': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'phone': user.phone,
                'bio': user.bio,
                'location': user.location,
                'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None,
                'date_joined': user.date_joined.isoformat(),
                'notification_email': user.notification_email,
                'notification_sms': user.notification_sms,
            },
            'messages_sent': list(messages),
            'sessions': list(sessions),
        }
        return Response(data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='me/close-account')
    def close_account(self, request):
        """GDPR Article 17 — anonymise the user's personal data and deactivate the account.
        The account record is retained for audit purposes but all identifying information is removed."""
        import uuid
        user = request.user
        anon_id = uuid.uuid4().hex[:12]

        user.first_name = 'Deleted'
        user.last_name = 'User'
        user.email = f'deleted-{anon_id}@removed.invalid'
        user.username = f'deleted-{anon_id}'
        user.phone = ''
        user.bio = ''
        user.location = ''
        user.date_of_birth = None
        user.profile_picture = None
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save()

        return Response({'status': 'account closed'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def export(self, request):
        """Export all users as CSV data."""
        from .exports import UserCSVExport
        return UserCSVExport.export(self.filter_queryset(self.get_queryset()))

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_upload(self, request):
        """Bulk upload users from CSV/XLSX."""
        from .imports import UserBulkImport
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        result = UserBulkImport.process(file, imported_by=request.user)
        return Response(result)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Mark a mentor as safeguarding-verified."""
        user = self.get_object()
        from django.utils import timezone
        user.is_verified = True
        user.safeguarding_training_date = request.data.get('training_date') or timezone.now().date()
        user.save(update_fields=['is_verified', 'safeguarding_training_date'])
        return Response({'status': 'verified'})

    @action(detail=True, methods=['get'])
    def activity_summary(self, request, pk=None):
        """Return recent messaging activity summary for a user."""
        user = self.get_object()
        from apps.messaging.models import Message
        from django.db.models import Max

        last_sent = Message.objects.filter(sender=user, status=Message.Status.DELIVERED).aggregate(last=Max('sent_at'))['last']
        last_received = Message.objects.filter(
            conversation__participants=user, status=Message.Status.DELIVERED
        ).exclude(sender=user).aggregate(last=Max('sent_at'))['last']

        return Response({
            'user_id': user.pk,
            'last_message_sent': last_sent,
            'last_message_received': last_received,
        })


class MentoringMatchViewSet(viewsets.ModelViewSet):
    """Manage mentor-scholar matches. Supports one mentor with multiple scholars."""
    queryset = MentoringMatch.objects.select_related('scholar', 'mentor').order_by('-matched_on')
    serializer_class = MentoringMatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['scholar', 'mentor', 'is_active']
    search_fields = ['scholar__first_name', 'scholar__last_name', 'mentor__first_name', 'mentor__last_name']

    def get_permissions(self):
        if self.action in ('create', 'destroy', 'update'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        match = serializer.save(matched_by=self.request.user)
        # Auto-create a direct conversation between the matched pair if one doesn't exist
        from apps.messaging.models import Conversation
        existing = Conversation.objects.filter(
            conversation_type=Conversation.ConversationType.DIRECT,
            participants=match.scholar,
        ).filter(participants=match.mentor)
        if not existing.exists():
            conv = Conversation.objects.create(
                conversation_type=Conversation.ConversationType.DIRECT,
                subject=f'{match.scholar.full_name} & {match.mentor.full_name}',
            )
            conv.participants.add(match.scholar, match.mentor)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def unmatched_scholars(self, request):
        """Return scholars with no active mentor match."""
        matched_ids = MentoringMatch.objects.filter(is_active=True).values_list('scholar_id', flat=True)
        scholars = User.objects.filter(role=User.Role.SCHOLAR, is_active=True).exclude(pk__in=matched_ids)
        return Response(UserListSerializer(scholars, many=True).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def mentors_with_capacity(self, request):
        """Return mentors who can accept more scholars."""
        from django.db.models import Count, Q
        mentors = User.objects.filter(role=User.Role.MENTOR, is_active=True).annotate(
            active_match_count=Count('mentor_matches', filter=Q(mentor_matches__is_active=True))
        ).filter(active_match_count__lt=3)  # default max
        return Response(UserListSerializer(mentors, many=True).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Return the authenticated user's own profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='mentors')
    def mentors(self, request):
        """
        Discoverable mentor list with avg_rating, discipline filter and availability.
        Used by the Mentor Discovery page.
        """
        from django.db.models import Avg, Count, Q
        from apps.sessions.models import AvailabilitySlot

        qs = User.objects.filter(role=User.Role.MENTOR, is_active=True)

        # Optional discipline filter
        discipline = request.query_params.get('discipline')
        if discipline:
            qs = qs.filter(engineering_discipline__icontains=discipline)

        # Annotate avg rating (from session feedback) and session count
        qs = qs.annotate(
            avg_rating=Avg('mentor_sessions__feedback__rating'),
            session_count=Count('mentor_sessions', filter=Q(mentor_sessions__status='completed')),
        )

        # Optional availability filter
        available_only = request.query_params.get('available') == '1'
        if available_only:
            booked_slots = AvailabilitySlot.objects.filter(
                is_booked=False,
                start_time__gt=timezone.now(),
                mentor__in=qs,
            ).values_list('mentor_id', flat=True).distinct()
            qs = qs.filter(pk__in=booked_slots)

        qs = qs.order_by('-avg_rating', 'last_name')

        data = UserListSerializer(qs, many=True).data
        # Merge annotations into the serialized output
        ann_map = {u.pk: {'avg_rating': u.avg_rating, 'session_count': u.session_count} for u in qs}
        for item in data:
            extra = ann_map.get(item['id'], {})
            item['avg_rating'] = round(extra.get('avg_rating') or 0, 1)
            item['session_count'] = extra.get('session_count') or 0

        return Response(data)


class MentorWaitingListViewSet(viewsets.ModelViewSet):
    """Scholar waiting list for mentor assignment."""
    serializer_class = MentorWaitingListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_matched', 'engineering_discipline']
    search_fields = ['scholar__first_name', 'scholar__last_name', 'engineering_discipline']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return MentorWaitingList.objects.select_related('scholar', 'preferred_mentor').all()
        return MentorWaitingList.objects.filter(scholar=user)

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(scholar=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def match(self, request, pk=None):
        """Mark a waiting list entry as matched."""
        entry = self.get_object()
        entry.is_matched = True
        entry.matched_at = timezone.now()
        entry.save(update_fields=['is_matched', 'matched_at'])
        return Response(MentorWaitingListSerializer(entry).data)
