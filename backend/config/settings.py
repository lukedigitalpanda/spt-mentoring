"""
SPT Mentoring Platform - Django Settings
"""
import os
from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'import_export',
    'simple_history',
    'guardian',
    'channels',
    'tinymce',
    # Local apps
    'apps.users',
    'apps.messaging',
    'apps.cohorts',
    'apps.forums',
    'apps.resources',
    'apps.news',
    'apps.surveys',
    'apps.reports',
    'apps.moderation',
    'apps.sessions',
    'apps.notifications',
    'apps.goals',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='spt_mentoring'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Authentication
AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/hour',
        'user': '600/hour',
        'login': '10/minute',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SPT Mentoring Platform API',
    'DESCRIPTION': 'API for the SPT Scholar Mentoring Platform',
    'VERSION': '1.0.0',
}

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://mentoring.smallpeice.online',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# ── Security headers ──────────────────────────────────────────────────────────
# Always set (safe in both dev and prod)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Trust the reverse proxy's X-Forwarded-Proto so request.scheme is 'https' behind
# nginx. This must be set regardless of DEBUG: production currently runs with
# DEBUG=True, and without this Django builds absolute media/file URLs as http://,
# which the browser then blocks as mixed content on the https:// site.
# Safe locally too — the header is simply absent when there's no proxy.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS-only settings — only enforce when not running locally
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Strict'
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Redis / Celery
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Channels (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

# File storage
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Use S3 in production
USE_S3 = config('USE_S3', default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='eu-west-2')
    AWS_DEFAULT_ACL = 'private'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Email
EMAIL_BACKEND = config('EMAIL_BACKEND', default='config.logging_email_backend.LoggingEmailBackend')
LOGGED_EMAIL_BACKEND = config('LOGGED_EMAIL_BACKEND', default='config.smtp2go_backend.SMTP2GOEmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='mentoring@spt.org')

# Notification email debounce (N-3)
# Emails for message / forum notifications are batched per recipient: held for
# DEBOUNCE_SECONDS (sliding as new ones arrive) but never longer than
# MAX_DELAY_SECONDS from when the window first opened.
NOTIFICATION_EMAIL_DEBOUNCE_SECONDS = config('NOTIFICATION_EMAIL_DEBOUNCE_SECONDS', default=300, cast=int)
NOTIFICATION_EMAIL_MAX_DELAY_SECONDS = config('NOTIFICATION_EMAIL_MAX_DELAY_SECONDS', default=900, cast=int)
EMAIL_LOG_RETENTION_DAYS = config('EMAIL_LOG_RETENTION_DAYS', default=90, cast=int)

# Web Push / VAPID
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='')
VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY', default='')
VAPID_ADMIN_EMAIL = config('VAPID_ADMIN_EMAIL', default='admin@spt.org')

# Frontend URL — used in password reset emails
FRONTEND_URL = config('FRONTEND_URL', default='https://mentoring.smallpeice.online')

# Mentoring-specific settings
MENTORING_FROM_EMAIL = config('MENTORING_FROM_EMAIL', default='mentoring@spt.org')
SCHOLARSHIPS_FROM_EMAIL = config('SCHOLARSHIPS_FROM_EMAIL', default='scholarships@spt.org')
NO_CONTACT_REMINDER_DAYS = config('NO_CONTACT_REMINDER_DAYS', default=14, cast=int)

# Safeguarding / Moderation
MODERATION_BLOCKED_TERMS_FILE = BASE_DIR / 'config' / 'blocked_terms.txt'

# Guardian
ANONYMOUS_USER_NAME = None
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps.moderation': {'handlers': ['console', 'file'], 'level': 'WARNING', 'propagate': False},
    },
}

# ── Jazzmin admin theme ───────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # ── Branding ──────────────────────────────────────────────────────────────
    "site_title": "SPT Mentoring Admin",
    "site_header": "SPT Mentoring",
    "site_brand": "Mentoring",
    "site_logo": "admin/img/sptlogo.webp",
    "login_logo": "admin/img/sptlogo.webp",
    "login_logo_dark": "admin/img/sptlogo.webp",
    "site_logo_classes": None,
    "site_icon": None,
    "welcome_sign": "Helping young people become future engineers",
    "copyright": "Smallpeice Trust",

    # ── Search ────────────────────────────────────────────────────────────────
    "search_model": ["users.User"],
    "user_avatar": None,

    # ── Top menu ──────────────────────────────────────────────────────────────
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "https://mentoring.smallpeice.online", "new_window": True},
        {"app": "users"},
    ],

    # ── User dropdown ─────────────────────────────────────────────────────────
    "usermenu_links": [
        {"name": "View Site", "url": "https://mentoring.smallpeice.online", "new_window": True},
        {"model": "users.User"},
    ],

    # ── Sidebar nav ───────────────────────────────────────────────────────────
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["auth", "guardian"],
    "hide_models": [],

    # Order sidebar sections
    "order_with_respect_to": [
        "users",
        "messaging",
        "forums",
        "cohorts",
        "resources",
        "news",
        "surveys",
        "sessions",
        "goals",
        "moderation",
        "notifications",
        "reports",
    ],

    # Custom sidebar links (Matching Wizard, Reports)
    "custom_links": {
        "users": [
            {
                "name": "Matching Wizard",
                "url": "admin:users_mentoringmatch_wizard",
                "icon": "fas fa-magic",
                "permissions": ["users.add_mentoringmatch"],
            }
        ],
        "reports": [
            {
                "name": "Mentoring Report",
                "url": "/admin/reports/mentoringreport/",
                "icon": "fas fa-chart-bar",
            }
        ],
    },

    # ── Model icons ───────────────────────────────────────────────────────────
    "icons": {
        "users.User":               "fas fa-user",
        "users.MentoringMatch":     "fas fa-handshake",
        "users.ScholarProfile":     "fas fa-graduation-cap",
        "users.MentorProfile":      "fas fa-chalkboard-teacher",
        "users.SponsorProfile":     "fas fa-building",
        "users.MentorWaitingList":  "fas fa-clock",
        "messaging.Conversation":   "fas fa-comments",
        "messaging.Message":        "fas fa-envelope",
        "messaging.AbuseReport":    "fas fa-flag",
        "messaging.MassMessage":    "fas fa-bullhorn",
        "forums.Forum":             "fas fa-layer-group",
        "forums.Thread":            "fas fa-list-ul",
        "forums.Post":              "fas fa-comment-alt",
        "cohorts.Programme":        "fas fa-project-diagram",
        "cohorts.Cohort":           "fas fa-users",
        "cohorts.CohortMembership": "fas fa-user-check",
        "cohorts.SiteSettings":     "fas fa-cog",
        "resources.ResourceCategory": "fas fa-folder",
        "resources.Resource":       "fas fa-file-alt",
        "resources.SharedDocument": "fas fa-file-upload",
        "news.NewsItem":            "fas fa-newspaper",
        "news.PromotionalBanner":   "fas fa-ad",
        "surveys.Survey":           "fas fa-poll",
        "surveys.Question":         "fas fa-question-circle",
        "surveys.SurveyResponse":   "fas fa-check-square",
        "sessions.AvailabilitySlot": "fas fa-calendar",
        "sessions.MentoringSession": "fas fa-calendar-check",
        "sessions.SessionFeedback": "fas fa-star",
        "goals.Goal":               "fas fa-bullseye",
        "goals.GoalMilestone":      "fas fa-flag-checkered",
        "moderation.ModerationTerm": "fas fa-filter",
        "moderation.BlockedTerm":   "fas fa-ban",
        "moderation.FlaggedTerm":   "fas fa-exclamation-triangle",
        "moderation.ModerationLog": "fas fa-clipboard-list",
        "notifications.Notification": "fas fa-bell",
        "notifications.PushSubscription":  "fas fa-mobile-alt",
        "notifications.EmailCatalogueEntry": "fas fa-book",
        "notifications.EmailLog": "fas fa-inbox",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # ── Related modal ─────────────────────────────────────────────────────────
    "related_modal_active": False,

    # ── Custom assets ─────────────────────────────────────────────────────────
    "custom_css": "admin/css/jazzmin.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,

    # ── Change form layout ────────────────────────────────────────────────────
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user": "collapsible",
        "users.scholarprofile": "collapsible",
        "users.mentorprofile": "collapsible",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-purple",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}


# --- JaaS (8x8) video calls ---
JAAS_APP_ID = config('JAAS_APP_ID', default='')
JAAS_KID = config('JAAS_KID', default='')
# Private key is stored single-line in .env with literal \n; restore real newlines.
JAAS_PRIVATE_KEY = config('JAAS_PRIVATE_KEY', default='').replace('\\n', '\n')
JAAS_ENABLED = bool(JAAS_APP_ID and JAAS_KID and JAAS_PRIVATE_KEY)


# --- TinyMCE (rich text editor for News articles and Mass messages) ---
# The toolbar is deliberately small: it only exposes formatting the
# sanitiser (apps.news.sanitiser.sanitise_rich_text) actually keeps, so the
# editor never lets an admin author markup that gets silently stripped on
# save.
TINYMCE_DEFAULT_CONFIG = {
    'menubar': False,
    'plugins': 'lists link',
    'toolbar': 'bold italic underline forecolor | bullist numlist | link | removeformat',
    'branding': False,
    'height': 320,
}
