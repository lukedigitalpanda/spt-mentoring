from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProgrammeViewSet, CohortViewSet, CohortMembershipViewSet, SiteSettingsView

router = DefaultRouter()
router.register(r'programmes', ProgrammeViewSet, basename='programme')
router.register(r'cohorts', CohortViewSet, basename='cohort')
router.register(r'memberships', CohortMembershipViewSet, basename='membership')

urlpatterns = [
    path('settings/', SiteSettingsView.as_view(), name='site-settings'),
    path('', include(router.urls)),
]
