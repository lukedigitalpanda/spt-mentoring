from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResourceCategoryViewSet, ResourceViewSet, SharedDocumentViewSet

router = DefaultRouter()
router.register(r'categories', ResourceCategoryViewSet, basename='resource-category')
router.register(r'', ResourceViewSet, basename='resource')
router.register(r'shared-documents', SharedDocumentViewSet, basename='shared-document')

urlpatterns = [path('', include(router.urls))]
