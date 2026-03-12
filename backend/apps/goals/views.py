from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Goal, GoalMilestone
from .serializers import GoalSerializer, GoalMilestoneSerializer


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return Goal.objects.prefetch_related('milestones').all()
        return Goal.objects.filter(user=user).prefetch_related('milestones')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalMilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = GoalMilestoneSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['goal', 'is_completed']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == 'admin':
            return GoalMilestone.objects.select_related('goal').all()
        return GoalMilestone.objects.filter(goal__user=user)
