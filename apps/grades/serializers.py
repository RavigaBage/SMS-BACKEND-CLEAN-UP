from rest_framework import serializers
from django.db.models import Avg, F, Window
from django.db.models.functions import Rank
from rest_framework import serializers
from .models import Student,Grade
from apps.academic.models import Subject,Class
from apps.academic.serializers import  SubjectSerializer
from .Utils import AcademicReportGenerator,GradeCalculator


class StudentMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = Student
        fields = ['id', 'admission_number', 'first_name', 'last_name', 'full_name', 'status']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"



class GradeSerializer(serializers.ModelSerializer):
    # Read-only nested serializers
    student = StudentMinimalSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    
    # Write-only fields for creating/updating
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True,
        required=False
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True,
        required=False
    )
    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_obj',  # This matches your model field name
        write_only=True,
        required=False
    )
    
    # Computed fields
    percentage = serializers.SerializerMethodField()
    subject_rank = serializers.SerializerMethodField()
    class_average = serializers.SerializerMethodField() 

    class Meta:
        model = Grade
        fields = [
            'id', 'student', 'subject', 'academic_year', 'term',
            'total_score', 'grade_letter', 'percentage', 'subject_rank', 
            'class_average', 'assessment_score','assessment_total','test_score','test_total',
            'exam_score','exam_total','weighted_assessment','weighted_test',
            'weighted_exam',
            # Add write-only fields
            'student_id', 'subject_id', 'class_id'
        ]

    def get_percentage(self, obj):
        total_possible = getattr(obj, 'exam_total', 100) 
        return round(float((obj.total_score / total_possible) * 100), 2) if total_possible > 0 else 0

    def get_subject_rank(self, obj):
        ranks_dict = self.context.get('subject_ranks', {})
        key = (obj.student_id, obj.subject_id, obj.term)
        return ranks_dict.get(key)

    def get_class_average(self, obj):
        averages_dict = self.context.get('subject_averages', {})
        key = (obj.subject_id, obj.term)
        return averages_dict.get(key)

    def validate(self, data):
        """
        Validate that the combination is unique (only on create)
        """
        if not self.instance:  # Only validate on create, not update
            student = data.get('student')
            class_obj = data.get('class_obj')
            subject = data.get('subject')
            academic_year = data.get('academic_year')
            term = data.get('term')

            if all([student, class_obj, subject, academic_year, term]):
                # Check if grade already exists
                existing = Grade.objects.filter(
                    student=student,
                    class_obj=class_obj,
                    subject=subject,
                    academic_year=academic_year,
                    term=term
                ).exists()

                if existing:
                    raise serializers.ValidationError(
                        "A grade already exists for this student, class, subject, academic year, and term."
                    )

        return data

class StudentTranscriptSerializer(serializers.ModelSerializer):
    grades = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'admission_number', 'summary', 'grades']

    def get_summary(self, obj):
        enrollment = obj.enrollments.first()
        if not enrollment: return None
        
        target_year = str(enrollment.class_obj.academic_year).split(' ')[0].replace('/', '-')
        # Assume First Term if not specified, or pull from latest grade
        term = obj.academic_grades.filter(academic_year=target_year).values_list('term', flat=True).first() or "First Term"

        rank_data = AcademicReportGenerator.get_specific_student_rank(
            obj.id, enrollment.class_obj, target_year, term
        )
        
        return {
            "class_name": enrollment.class_obj.class_name,
            "academic_year": target_year,
            "term": term,
            "rank": rank_data.get('rank'),
            "total_students": rank_data.get('total_students'),
            "average_score": rank_data.get('average_score'),
            "gpa": rank_data.get('gpa')
        }

    def get_grades(self, obj):
        enrollment = obj.enrollments.first()
        if not enrollment: return []
        
        target_year = str(enrollment.class_obj.academic_year).split(' ')[0].replace('/', '-')
        grades_queryset = obj.academic_grades.filter(academic_year=target_year)

        # Context injection for high performance
        s_map = AcademicReportGenerator.get_subject_ranks_dict(enrollment.class_obj_id, target_year)
        avg_map = AcademicReportGenerator.get_subject_averages(enrollment.class_obj_id, target_year)

        return GradeSerializer(
            grades_queryset, 
            many=True, 
            context={'subject_ranks': s_map, 'subject_averages': avg_map}
        ).data


class ClassStudentListSerializer(serializers.ModelSerializer):
    """
    Serializer for the listing view of students within the TranscriptViewSet.
    Provides basic info plus current enrollment details.
    """
    full_name = serializers.SerializerMethodField()
    current_class = serializers.SerializerMethodField()
    admission_no = serializers.CharField(source='admission_number')

    class Meta:
        model = Student
        fields = [
            'id', 
            'admission_no', 
            'first_name', 
            'last_name', 
            'full_name', 
            'status', 
            'current_class', 
            'photo_url'
        ]

    def get_full_name(self, obj):
        return obj.full_name # Uses the @property from your Student model

    def get_current_class(self, obj):
        """
        Retrieves the class name for the student. 
        Tries to use the academic_year from context if provided in query params.
        """
        academic_year = self.context.get('academic_year')
        enrollment = obj.enrollments.all()
        
        if academic_year:
            enrollment = enrollment.filter(class_obj__academic_year=academic_year)
        
        enrollment = enrollment.select_related('class_obj').first()
        
        if enrollment:
            return enrollment.class_obj.class_name
        return "Not Enrolled"
# -----------------------------
# 5. Ranking Utilities
# -----------------------------
def get_subject_ranks(class_id, academic_year_str):
        # Ensure we are filtering by the string value of the year
        grades = Grade.objects.filter(
            class_obj_id=class_id, 
            academic_year=str(academic_year_str) 
        ).annotate(
            rank=Window(
                expression=Rank(), 
                partition_by=[F('subject_id'), F('term')], 
                order_by=F('total_score').desc()
            )
        )

        # Force keys to standard types: (int, int, str)
        return {
            (int(g.student_id), int(g.subject_id), str(g.term)): g.rank 
            for g in grades
        }
