from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MentoringMatchViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'matches', MentoringMatchViewSet, basename='match')

urlpatterns = [path('', include(router.urls))]
