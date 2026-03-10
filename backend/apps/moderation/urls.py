from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlockedTermViewSet, FlaggedTermViewSet, ModerationLogViewSet, FlaggedMessageViewSet

router = DefaultRouter()
router.register(r'blocked-terms', BlockedTermViewSet, basename='blocked-term')
router.register(r'flagged-terms', FlaggedTermViewSet, basename='flagged-term')
router.register(r'logs', ModerationLogViewSet, basename='moderation-log')
router.register(r'flagged-messages', FlaggedMessageViewSet, basename='flagged-message')

urlpatterns = [path('', include(router.urls))]
