from rest_framework import serializers
from typing import List, Dict, Any, Optional
from drf_spectacular.utils import extend_schema_field
from apps.academic.models import Class
from .models import Student, Parent, StudentParent


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    relationship_display = serializers.CharField(
        source="get_relationship_display",
        read_only=True
    )

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "email",
            "address",
            "occupation",
            "workplace",
            "national_id",
            "relationship",
            "relationship_display",
            "created_at",
            "updated_at",
           
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ["id", "class_name", "grade_level"]

class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    class_info = ClassSerializer(source='class_obj', read_only=True)
    gender_display = serializers.CharField(
        source="get_gender_display",
        read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )

    class Meta:
        model = Student
        fields = [
            "id",
            "admission_number",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "gender_display",
            "address",
            "nationality",
            "religion",
            "blood_group",
            "medical_conditions",
            "status",
            "status_display",
            "admission_date",
            "photo_url",
            "created_at",
            "updated_at",
            "class_info"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    parents = serializers.SerializerMethodField()
    current_class = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "admission_number",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "address",
            "nationality",
            "religion",
            "blood_group",
            "medical_conditions",
            "status",
            "admission_date",
            "photo_url",
            "parents",
            "current_class",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_parents(self, obj) -> List[Dict[str, Any]]:
        links = obj.parent_links.select_related("parent")
        return [
            {
                "parent": ParentSerializer(link.parent).data,
                "is_primary_contact": link.is_primary_contact,
                "can_pickup": link.can_pickup,
            }
            for link in links
        ]


    @extend_schema_field(serializers.DictField())
    def get_current_class(self, obj):
        # Get the active enrollment
        enrollment = obj.enrollments.filter(status="active").select_related("class_obj").first()
        if enrollment:
            return {
                "id": enrollment.class_obj.id,
                "name": enrollment.class_obj.class_name,
                "grade_level": enrollment.class_obj.grade_level,
                "section": enrollment.class_obj.section,
                "academic_year": enrollment.class_obj.academic_year.year_name
            }
        return None


class StudentCreateSerializer(serializers.Serializer):
    admission_number = serializers.CharField(max_length=50)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    middle_name = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=Student.Gender.choices)

    address = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_blank=True)
    religion = serializers.CharField(required=False, allow_blank=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)
    medical_conditions = serializers.CharField(required=False, allow_blank=True)

    admission_date = serializers.DateField()
    photo_url = serializers.URLField(required=False, allow_blank=True)

    class_id = serializers.IntegerField(required=False, allow_null=True)
    parents = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "middle_name",
            "date_of_birth",
            "gender",
            "address",
            "nationality",
            "religion",
            "blood_group",
            "medical_conditions",
            "status",
            "photo_url",
        ]


class StudentParentSerializer(serializers.ModelSerializer):
    # We change these to PrimaryKeyRelatedFields so they accept IDs on POST/PUT
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    parent = serializers.PrimaryKeyRelatedField(queryset=Parent.objects.all())

    class Meta:
        model = StudentParent
        fields = [
            "id",
            "student",
            "parent",
            "is_primary_contact",
            "can_pickup",
        ]

    def to_representation(self, instance):
        """
        This method allows us to return the FULL nested data for GET requests
        while still accepting just the ID for POST requests.
        """
        response = super().to_representation(instance)
        response['student'] = StudentSerializer(instance.student).data
        response['parent'] = ParentSerializer(instance.parent).data
        return response