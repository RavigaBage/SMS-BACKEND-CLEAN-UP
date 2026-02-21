# apps/settings/urls.py

from django.urls import path
from .views import email_settings, test_email

urlpatterns = [
    path("settings/email/", email_settings),
    path("settings/email/test/", test_email),
]
