from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet, MassMessageViewSet, AbuseReportViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'mass-messages', MassMessageViewSet, basename='mass-message')
router.register(r'abuse-reports', AbuseReportViewSet, basename='abuse-report')

urlpatterns = [path('', include(router.urls))]
