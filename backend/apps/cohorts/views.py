from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Programme, Cohort, CohortMembership
from .serializers import ProgrammeSerializer, CohortSerializer, CohortMembershipSerializer


class ProgrammeViewSet(viewsets.ModelViewSet):
    queryset = Programme.objects.all().order_by('-start_date')
    serializer_class = ProgrammeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]


class CohortViewSet(viewsets.ModelViewSet):
    queryset = Cohort.objects.select_related('programme').order_by('-year')
    serializer_class = CohortSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['programme', 'year', 'is_active']
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'bulk_assign'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_assign(self, request, pk=None):
        """Assign a list of user IDs to this cohort."""
        cohort = self.get_object()
        user_ids = request.data.get('user_ids', [])
        from apps.users.models import User
        users = User.objects.filter(pk__in=user_ids)
        created = 0
        for user in users:
            _, was_created = CohortMembership.objects.get_or_create(cohort=cohort, user=user)
            if was_created:
                created += 1
        return Response({'assigned': created, 'total': len(user_ids)})


class CohortMembershipViewSet(viewsets.ModelViewSet):
    queryset = CohortMembership.objects.select_related('cohort', 'user').all()
    serializer_class = CohortMembershipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cohort', 'user']

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]
