from rest_framework import serializers
from .models import AcademicYear, Class, Subject, Enrollment, SubjectAssignment,Student,Teacher
from apps.students.serializers import StudentSerializer
from apps.teachers.serializers import TeacherSerializer


class AcademicYearSerializer(serializers.ModelSerializer):
    """Serializer for AcademicYear model"""
    
    class Meta:
        model = AcademicYear
        fields = ['id', 'year_name', 'start_date', 'end_date', 'is_current']
        read_only_fields = ['id']


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""
    
    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'subject_code', 'description', 'grade_level']
        read_only_fields = ['id']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model"""
    
    teacher_name = serializers.CharField(source='class_teacher.__str__', read_only=True)
    
    class_teacher = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        required=False,
        allow_null=True
    )
    class_teacher_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    academic_year_name = serializers.CharField(source='academic_year.year_name', read_only=True)
    current_enrollment = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Class
        fields = [
            'id', 'class_name', 'grade_level', 'section',
            'academic_year', 'academic_year_name','class_teacher', 'teacher_name', 'class_teacher_id',
            'capacity', 'current_enrollment', 'room_number'
        ]
        read_only_fields = ['id']


class EnrollmentSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), 
        source='student', 
        write_only=True
    )

    class_obj = ClassSerializer(read_only=True)
    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), 
        source='class_obj', 
        write_only=True
    )
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_id', 'class_obj', 'class_id',
            'enrollment_date', 'status', 'status_display', 'roll_number'
        ]
        read_only_fields = ['id', 'enrollment_date']

class SubjectAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for SubjectAssignment model"""
    
    class_obj = ClassSerializer(read_only=True)
    class_id = serializers.IntegerField(write_only=True, source='class_obj')
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.IntegerField(write_only=True)
    teacher = serializers.SerializerMethodField()
    teacher_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = SubjectAssignment
        fields = [
            'id', 'class_obj', 'class_id', 'subject', 'subject_id',
            'teacher', 'teacher_id'
        ]
        read_only_fields = ['id']


class ClassDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Class with enrollments and subjects"""
    
    class_teacher = serializers.SerializerMethodField()
    academic_year = AcademicYearSerializer(read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    subject_assignments = SubjectAssignmentSerializer(many=True, read_only=True)
    current_enrollment = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Class
        fields = [
            'id', 'class_name', 'grade_level', 'section',
            'academic_year', 'class_teacher', 'capacity',
            'current_enrollment', 'room_number',
            'enrollments', 'subject_assignments'
        ]

class AssignedClassSerializer(serializers.ModelSerializer):
    """Stand-alone: No imports needed from Staff"""
    academic_year_name = serializers.CharField(source='academic_year.year_name', read_only=True)
    
    class Meta:
        model = Class
        fields = ['id', 'class_name', 'grade_level', 'section', 'academic_year_name', 'room_number']