from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import ResourceCategory, Resource, SharedDocument
from .serializers import ResourceCategorySerializer, ResourceSerializer, SharedDocumentSerializer


class ResourceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]


class ResourceViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['resource_type', 'audience', 'programme', 'category', 'is_active']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title', 'download_count']

    def get_queryset(self):
        user = self.request.user
        qs = Resource.objects.filter(is_active=True)
        if not (user.is_staff or user.role == 'admin'):
            from django.db.models import Q
            qs = qs.filter(Q(audience='all') | Q(audience=user.role))
        return qs

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        resource = self.get_object()
        resource.download_count += 1
        resource.save(update_fields=['download_count'])
        return Response({'download_url': resource.file.url if resource.file else resource.url})


class SharedDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = SharedDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        return SharedDocument.objects.filter(
            Q(shared_by=user) | Q(shared_with=user)
        )

    def perform_create(self, serializer):
        serializer.save(shared_by=self.request.user)
