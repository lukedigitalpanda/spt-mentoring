from rest_framework.routers import DefaultRouter
from .views import GoalViewSet, GoalMilestoneViewSet

router = DefaultRouter()
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'milestones', GoalMilestoneViewSet, basename='goal-milestone')

urlpatterns = router.urls
