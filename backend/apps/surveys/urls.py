from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SurveyViewSet, SurveyResponseViewSet

router = DefaultRouter()
router.register(r'surveys', SurveyViewSet, basename='survey')
router.register(r'responses', SurveyResponseViewSet, basename='survey-response')

urlpatterns = [path('', include(router.urls))]
