from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import NewsItem, PromotionalBanner
from .serializers import NewsItemSerializer, PromotionalBannerSerializer


class NewsItemViewSet(viewsets.ModelViewSet):
    serializer_class = NewsItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'audience', 'programme', 'is_featured']
    search_fields = ['title', 'summary', 'body']
    ordering_fields = ['published_at', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = NewsItem.objects.all()
        if not (user.is_staff or user.role == 'admin'):
            from django.db.models import Q
            qs = qs.filter(status='published').filter(
                Q(audience='all') | Q(audience=user.role)
            )
        return qs.order_by('-published_at')

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PromotionalBannerViewSet(viewsets.ModelViewSet):
    queryset = PromotionalBanner.objects.filter(is_active=True).order_by('order')
    serializer_class = PromotionalBannerSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]
