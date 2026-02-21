# apps/settings/utils.py

from django.conf import settings
from .models import EmailConfiguration

def apply_email_config():
    try:
        config = EmailConfiguration.objects.first()
        if not config:
            return

        if config.backend == "console":
            settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
        else:
            settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
            settings.EMAIL_HOST = config.host
            settings.EMAIL_PORT = config.port
            settings.EMAIL_USE_TLS = config.use_tls
            settings.EMAIL_HOST_USER = config.host_user
            settings.EMAIL_HOST_PASSWORD = config.host_password
            settings.DEFAULT_FROM_EMAIL = config.default_from_email
    except:
        pass
