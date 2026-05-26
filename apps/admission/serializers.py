from rest_framework import serializers
from datetime import date
import re
from .models import Admission


class AdmissionSerializer(serializers.ModelSerializer):

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = '__all__'
        read_only_fields = ['approval_state']


    def validate_date_of_birth(self, value):

        today = date.today()

        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )

        if age < 2:
            raise serializers.ValidationError("Applicant too young.")

        return value

    def validate_admission_number(self, value):

        if value and not re.match(r"^ADM-\d{4,10}$", value):
            raise serializers.ValidationError(
                "Invalid format. Use ADM-0001 style."
            )

        return value


    def validate(self, data):

        errors = {}

        if not data.get('has_normal_health') and not data.get('health_condition_details', '').strip():
            errors['health_condition_details'] = "Health details required."

        if not data.get('has_normal_hearing') and not data.get('hearing_condition_details', '').strip():
            errors['hearing_condition_details'] = "Hearing details required."

        if data.get('has_psychological_trauma') and not data.get('psychological_trauma_details', '').strip():
            errors['psychological_trauma_details'] = "Please explain trauma."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    

    def get_full_name(self, obj):
        return f"{obj.surname} {obj.middle_name or ''} {obj.first_name}"