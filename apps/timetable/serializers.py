from rest_framework import serializers
from .models import Timetable
from apps.academic.serializers import ClassSerializer, SubjectSerializer
from apps.staff.serializers import StaffSerializer

from rest_framework import serializers
from .models import Syllabus
from apps.teachers.models import Teacher
from apps.academic.models import Class,Subject



class TimetableSerializer(serializers.ModelSerializer):
    """Serializer for Timetable model"""
    
    class_obj = ClassSerializer(read_only=True)
    class_id = serializers.IntegerField(write_only=True, source='class_obj')
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.IntegerField(write_only=True)
    teacher = StaffSerializer(read_only=True)
    teacher_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Timetable
        fields = [
            'id', 'class_obj', 'class_id', 'subject', 'subject_id',
            'teacher', 'teacher_id', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time', 'room_number'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("Start time must be before end time")


class SyllabusSerializer(serializers.ModelSerializer):
    # Read-only nested serializers (for GET requests)
    subject = serializers.SerializerMethodField(read_only=True)
    teacher = serializers.SerializerMethodField(read_only=True)
    class_obj = serializers.SerializerMethodField(read_only=True)
    
    # Write-only fields (for POST/PUT/PATCH requests)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True,
        required=True
    )
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        required=True
    )
    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_obj',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Syllabus
        fields = [
            'id',
            'subject',
            'teacher',
            'class_obj',
            'subject_id',
            'teacher_id',
            'class_id',
            'week_number',
            'topic_title',
            'content_summary',
            'learning_objectives',
        ]
        read_only_fields = ['id']

    def get_subject(self, obj):
        """Return subject details"""
        return {
            'id': obj.subject.id,
            'subject_name': obj.subject.subject_name,
            'subject_code': getattr(obj.subject, 'subject_code', None),
        }

    def get_teacher(self, obj):
        """Return teacher details"""
        return {
            'id': obj.teacher.id,
            'first_name': obj.teacher.first_name,
            'last_name': obj.teacher.last_name,
            'full_name': f"{obj.teacher.first_name} {obj.teacher.last_name}",
        }

    def get_class_obj(self, obj):
        """Return class details"""
        if obj.class_obj:
            return {
                'id': obj.class_obj.id,
                'class_name': obj.class_obj.class_name,
            }
        return None

    def validate_week_number(self, value):
        """Validate that week number is positive"""
        if value < 1:
            raise serializers.ValidationError("Week number must be at least 1.")
        return value

    def validate(self, data):
        """
        Validate that the combination of subject, teacher, class, and week_number is unique
        """
        subject = data.get('subject')
        teacher = data.get('teacher')
        class_obj = data.get('class_obj')
        week_number = data.get('week_number')

        # Only validate on create or if these fields are being updated
        if not self.instance or any(key in data for key in ['subject', 'teacher', 'class_obj', 'week_number']):
            query = Syllabus.objects.filter(
                subject=subject,
                teacher=teacher,
                class_obj=class_obj,
                week_number=week_number
            )
            
            # Exclude current instance on update
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise serializers.ValidationError(
                    "A syllabus entry already exists for this subject, teacher, class, and week number."
                )

        return data


# Minimal serializer for nested use
class SyllabusMinimalSerializer(serializers.ModelSerializer):
    """Lightweight serializer for nested representations"""
    
    class Meta:
        model = Syllabus
        fields = [
            'id',
            'week_number',
            'topic_title',
            'content_summary',
        ]


# List serializer for displaying multiple syllabi
class SyllabusListSerializer(serializers.ModelSerializer):
    """Serializer optimized for list views"""
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='class_obj.class_name', read_only=True)

    class Meta:
        model = Syllabus
        fields = [
            'id',
            'subject_name',
            'teacher_name',
            'class_name',
            'week_number',
            'topic_title',
        ]

    def get_teacher_name(self, obj):
        return f"{obj.teacher.first_name} {obj.teacher.last_name}"