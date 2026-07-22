from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView as SpectacularSwaggerUIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle
from apps.users.auth_views import PasswordResetRequestView, PasswordResetConfirmView


class LoginRateThrottle(AnonRateThrottle):
    """Tight throttle on the login endpoint — 10 attempts per minute per IP."""
    rate = '10/minute'


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]


urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth — login is rate-limited to 10/min per IP; password reset is open
    path('api/auth/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('api/auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
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
    # Media files — always served by Django regardless of DEBUG mode.
    # The shared nginx terminates SSL and forwards X-Forwarded-Proto: https,
    # so all file URLs are generated as https:// and downloads are never blocked.
    re_path(r'^media/(?P<path>.+)$', serve, kwargs={'document_root': settings.MEDIA_ROOT}),
]
