from django.urls import path
from .views import (
    ScholarMentorContactReport,
    SponsorUpdateReport,
    UserDataReport,
    CohortProgressReport,
    ModerationReport,
)

urlpatterns = [
    path('contact/', ScholarMentorContactReport.as_view(), name='report-contact'),
    path('sponsor-updates/', SponsorUpdateReport.as_view(), name='report-sponsor-updates'),
    path('users/', UserDataReport.as_view(), name='report-users'),
    path('cohort-progress/', CohortProgressReport.as_view(), name='report-cohort-progress'),
    path('moderation/', ModerationReport.as_view(), name='report-moderation'),
]
