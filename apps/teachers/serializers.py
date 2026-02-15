from rest_framework import serializers
from .models import Teacher
from apps.accounts.serializers import UserSerializer

class TeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teacher model"""
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    subject_list = serializers.CharField(read_only=True)
    subjects = serializers.SerializerMethodField()
    assigned_by_username = serializers.CharField(
        source='assigned_by.username', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Teacher
        fields = [
            'id',
            'user',
            'first_name',
            'last_name',
            'full_name',
            'specialization',
            'subjects',
            'subject_list',
            'qualifications',
            'years_of_experience',
            'phone_number',
            'emergency_contact',
            'is_active',
            'date_joined',
            'assigned_by',
            'assigned_by_username',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']
    def get_subjects(self, obj):
        from apps.academic.serializers import SubjectSerializer
        return SubjectSerializer(obj.subjects.all(), many=True).data


class TeacherCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a Teacher"""
    user_id = serializers.IntegerField(write_only=True)
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of subject IDs to assign to this teacher"
    )
    
    class Meta:
        model = Teacher
        fields = [
            'user_id',
            'first_name',
            'last_name',
            'specialization',
            'subject_ids',
            'qualifications',
            'years_of_experience',
            'phone_number',
            'emergency_contact'
        ]
    
    def validate_user_id(self, value):
        """Validate that user exists and is a teacher"""
        from apps.accounts.models import User
        
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        
        if user.role != 'teacher':
            raise serializers.ValidationError("User must have 'teacher' role")
        
        # Check if teacher profile already exists
        if hasattr(user, 'teacher_profile'):
            raise serializers.ValidationError("Teacher profile already exists for this user")
        
        return value
    
    def validate_subject_ids(self, value):
        """Validate that all subject IDs exist"""
        from apps.academic.models import Subject
        
        if value:
            existing_subjects = Subject.objects.filter(id__in=value).count()
            if existing_subjects != len(value):
                raise serializers.ValidationError("One or more subject IDs are invalid")
        
        return value


class TeacherUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a Teacher"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of subject IDs to assign to this teacher"
    )
    
    class Meta:
        model = Teacher
        fields = [
            'first_name',
            'last_name',
            'specialization',
            'subject_ids',
            'qualifications',
            'years_of_experience',
            'phone_number',
            'emergency_contact',
            'is_active'
        ]
    
    def validate_subject_ids(self, value):
        """Validate that all subject IDs exist"""
        from apps.academic.models import Subject
        
        if value:
            existing_subjects = Subject.objects.filter(id__in=value).count()
            if existing_subjects != len(value):
                raise serializers.ValidationError("One or more subject IDs are invalid")
        
        return value


class TeacherAssignSubjectsSerializer(serializers.Serializer):
    """Serializer for assigning subjects to a teacher"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of subject IDs to assign"
    )
    
    def validate_subject_ids(self, value):
        """Validate that all subject IDs exist"""
        from apps.academic.models import Subject
        
        if not value:
            raise serializers.ValidationError("At least one subject ID is required")
        
        existing_subjects = Subject.objects.filter(id__in=value).count()
        if existing_subjects != len(value):
            raise serializers.ValidationError("One or more subject IDs are invalid")
        
        return value


class TeacherDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Teacher with all related information"""
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    subject_list = serializers.CharField(read_only=True)
    subjects = serializers.SerializerMethodField()
    assigned_by_username = serializers.CharField(
        source='assigned_by.username', 
        read_only=True,
        allow_null=True
    )
    assigned_classes_count = serializers.SerializerMethodField()
    subject_assignments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Teacher
        fields = [
            'id',
            'user',
            'first_name',
            'last_name',
            'full_name',
            'specialization',
            'subjects',
            'subject_list',
            'qualifications',
            'years_of_experience',
            'phone_number',
            'emergency_contact',
            'is_active',
            'date_joined',
            'assigned_by',
            'assigned_by_username',
            'assigned_classes_count',
            'subject_assignments_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']
    def get_subjects(self, obj):
        from apps.academic.serializers import SubjectSerializer
        return SubjectSerializer(obj.subjects.all(), many=True).data
    
    def get_assigned_classes_count(self, obj):
        """Get count of classes where teacher is class teacher"""
        return obj.get_assigned_classes().count()
    
    def get_subject_assignments_count(self, obj):
        """Get count of subject assignments"""
        return obj.get_subject_assignments().count()