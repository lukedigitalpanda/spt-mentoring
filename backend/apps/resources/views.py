from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import ResourceCategory, Resource, SharedDocument
from .serializers import ResourceCategorySerializer, ResourceSerializer, SharedDocumentSerializer


class ResourceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ResourceCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['parent']
    ordering_fields = ['order', 'name']

    def get_queryset(self):
        qs = ResourceCategory.objects.all()
        # ?root=true returns only top-level folders (no parent)
        if self.request.query_params.get('root') == 'true':
            qs = qs.filter(parent__isnull=True)
        return qs

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
            all_roles = user.all_roles
            # Build audience filter across all roles the user holds
            role_q = Q(audience_list=[], audience='all') | Q(audience_list__contains=['all'])
            for r in all_roles:
                role_q |= Q(audience_list=[], audience=r)
                role_q |= Q(audience_list__contains=[r])
            qs = qs.filter(role_q)
        if self.request.query_params.get('no_category') == 'true':
            qs = qs.filter(category__isnull=True)
        created_after = self.request.query_params.get('created_after')
        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
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
        # Staff get an unfiltered view so shared documents are always auditable.
        if user.is_staff or user.role == 'admin':
            return SharedDocument.objects.all()
        return SharedDocument.objects.filter(
            Q(shared_by=user) | Q(shared_with=user)
        )

    def perform_create(self, serializer):
        """Allow specifying recipient by email (shared_with_email) or by user ID (shared_with)."""
        from apps.users.models import User
        from rest_framework.exceptions import ValidationError
        recipient = serializer.validated_data.get('shared_with')
        if recipient is None:
            email = (self.request.data.get('shared_with_email') or '').strip()
            if not email:
                raise ValidationError({'shared_with': 'A recipient is required (shared_with or shared_with_email).'})
            try:
                recipient = User.objects.get(email=email, is_active=True)
            except User.DoesNotExist:
                raise ValidationError({'shared_with_email': 'No active user found with this email address.'})
        serializer.save(shared_by=self.request.user, shared_with=recipient)
