from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, MentoringMatch
from .serializers import (
    UserSerializer, UserListSerializer, UserCreateSerializer, MentoringMatchSerializer
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
        serializer.save(matched_by=self.request.user)

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
