from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProgrammeViewSet, CohortViewSet, CohortMembershipViewSet

router = DefaultRouter()
router.register(r'programmes', ProgrammeViewSet, basename='programme')
router.register(r'cohorts', CohortViewSet, basename='cohort')
router.register(r'memberships', CohortMembershipViewSet, basename='membership')

urlpatterns = [path('', include(router.urls))]
