from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ForumViewSet, ThreadViewSet, PostViewSet

router = DefaultRouter()
router.register(r'forums', ForumViewSet, basename='forum')
router.register(r'threads', ThreadViewSet, basename='thread')
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [path('', include(router.urls))]
