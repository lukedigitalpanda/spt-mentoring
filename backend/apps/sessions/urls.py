from rest_framework.routers import DefaultRouter
from .views import AvailabilitySlotViewSet, MentoringSessionViewSet, SessionFeedbackViewSet

router = DefaultRouter()
router.register(r'slots', AvailabilitySlotViewSet, basename='availability-slot')
router.register(r'sessions', MentoringSessionViewSet, basename='session')
router.register(r'feedback', SessionFeedbackViewSet, basename='session-feedback')

urlpatterns = router.urls
