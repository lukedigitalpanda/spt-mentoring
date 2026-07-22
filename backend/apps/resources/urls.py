from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceCategoryViewSet, ResourceViewSet, SharedDocumentViewSet

router = DefaultRouter()
# The catch-all '' prefix MUST be registered last: its detail route would
# otherwise swallow /shared-documents/ as a resource lookup (P2-3 root cause).
router.register(r'categories', ResourceCategoryViewSet, basename='resource-category')
router.register(r'shared-documents', SharedDocumentViewSet, basename='shared-document')
router.register(r'', ResourceViewSet, basename='resource')

urlpatterns = [path('', include(router.urls))]
