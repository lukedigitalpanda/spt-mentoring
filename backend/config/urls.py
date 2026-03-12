from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # App APIs
    path('api/users/', include('apps.users.urls')),
    path('api/messaging/', include('apps.messaging.urls')),
    path('api/cohorts/', include('apps.cohorts.urls')),
    path('api/forums/', include('apps.forums.urls')),
    path('api/resources/', include('apps.resources.urls')),
    path('api/news/', include('apps.news.urls')),
    path('api/surveys/', include('apps.surveys.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/moderation/', include('apps.moderation.urls')),
    path('api/sessions/', include('apps.sessions.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/goals/', include('apps.goals.urls')),
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerUIView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
