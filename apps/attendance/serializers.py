from rest_framework import serializers
from .models import Attendance
from apps.students.serializers import StudentSerializer
from apps.academic.serializers import ClassSerializer
from apps.students.models import Student
from apps.academic.models import Class

class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance model"""
    
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True
    )
    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_obj',
        write_only=True,
        required=False,
        allow_null=True
    )
    class_obj = ClassSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    marked_by_username = serializers.CharField(source='marked_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'student', 'student_id', 'class_obj', 'class_id',
            'attendance_date', 'status', 'status_display', 'remarks',
            'marked_by', 'marked_by_username', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for marking bulk attendance"""
    
    class_id = serializers.IntegerField()
    attendance_date = serializers.DateField()
    attendance_records = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate_attendance_records(self, value):
        for record in value:
            if 'student_id' not in record or 'status' not in record:
                raise serializers.ValidationError(
                    "Each attendance record must have 'student_id' and 'status'"
                )
        return value


class AttendanceReportSerializer(serializers.Serializer):
    """Serializer for attendance reports"""
    
    student = StudentSerializer(read_only=True)
    total_days = serializers.IntegerField(read_only=True)
    present_days = serializers.IntegerField(read_only=True)
    absent_days = serializers.IntegerField(read_only=True)
    late_days = serializers.IntegerField(read_only=True)
    excused_days = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)