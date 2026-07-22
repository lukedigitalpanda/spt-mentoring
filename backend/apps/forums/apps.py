from django.apps import AppConfig

class ForumsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.forums'
    verbose_name = 'Forums'

    def ready(self):
        import apps.forums.signals  # noqa: F401
