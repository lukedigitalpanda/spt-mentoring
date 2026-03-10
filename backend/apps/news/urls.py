from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NewsItemViewSet, PromotionalBannerViewSet

router = DefaultRouter()
router.register(r'items', NewsItemViewSet, basename='news-item')
router.register(r'banners', PromotionalBannerViewSet, basename='banner')

urlpatterns = [path('', include(router.urls))]
