from rest_framework import serializers
from apps.teachers.models import Teacher
from apps.accounts.serializers import UserSerializer

class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "user", "first_name", "last_name", "specialization"]

