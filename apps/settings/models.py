
from django.db import models

class EmailConfiguration(models.Model):
    BACKEND_CHOICES = [
        ("console", "Console"),
        ("smtp", "SMTP"),
    ]

    backend = models.CharField(max_length=20, choices=BACKEND_CHOICES, default="console")
    host = models.CharField(max_length=255, blank=True)
    port = models.IntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    host_user = models.CharField(max_length=255, blank=True)
    host_password = models.CharField(max_length=255, blank=True)
    default_from_email = models.CharField(max_length=255, blank=True)
    school_name = models.CharField(max_length=255, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Email Configuration"
