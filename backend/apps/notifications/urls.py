from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, PushSubscriptionViewSet

router = DefaultRouter()
router.register(r'push-subscriptions', PushSubscriptionViewSet, basename='push-subscription')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = router.urls
