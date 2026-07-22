from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MentoringMatchViewSet, MentorWaitingListViewSet

router = DefaultRouter()
# The catch-all '' prefix MUST be registered last: its detail route
# (^(?P<pk>[^/.]+)/$) would otherwise swallow /matches/ and /waiting-list/
# as a user lookup with pk='matches' / pk='waiting-list' (404).
router.register(r'matches', MentoringMatchViewSet, basename='match')
router.register(r'waiting-list', MentorWaitingListViewSet, basename='waiting-list')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [path('', include(router.urls))]
