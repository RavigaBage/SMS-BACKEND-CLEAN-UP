# apps/settings/serializers.py

from rest_framework import serializers
from .models import EmailConfiguration

class EmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfiguration
        fields = "__all__"
