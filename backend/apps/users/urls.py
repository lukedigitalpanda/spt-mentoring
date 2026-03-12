from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MentoringMatchViewSet, MentorWaitingListViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'matches', MentoringMatchViewSet, basename='match')
router.register(r'waiting-list', MentorWaitingListViewSet, basename='waiting-list')

urlpatterns = [path('', include(router.urls))]
