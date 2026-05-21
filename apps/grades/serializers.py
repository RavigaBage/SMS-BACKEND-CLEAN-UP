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
    student = StudentMinimalSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True,
        required=False
    )

    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_obj', 
        write_only=True,
        required=False
    )
    
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
            'weighted_exam','remarks','student_id', 'subject_id', 'class_id'
        ]

    def get_percentage(self, obj):
        return round(float(obj.total_score), 2) if obj.total_score is not None else 0

    def get_subject_rank(self, obj):
        ranks_dict = self.context.get('subject_ranks', {})
        key = (int(obj.student_id), int(obj.subject_id), str(obj.term))
        
        if not ranks_dict:
            print("WARNING: subject_ranks context is empty or missing")
        else:
            print(f"Looking up key: {key}")
            print(f"Available keys sample: {list(ranks_dict.keys())[:3]}")
        
        return ranks_dict.get(key)

    def get_class_average(self, obj):
        averages_dict = self.context.get('subject_averages', {})
        key = (obj.subject_id, obj.term)
        return averages_dict.get(key)

    def validate(self, data):
        """
        Validate that the combination is unique (only on create)
        """
        class_obj = data.get('class_obj') or getattr(self.instance, 'class_obj', None)
        subject = data.get('subject') or getattr(self.instance, 'subject', None)

        if class_obj and subject and not class_obj.subjects.filter(pk=subject.pk).exists():
            raise serializers.ValidationError(
                "this subject has not been assigned to this class, contact your administrator."
            )

        if not self.instance: 
            student = data.get('student')
            academic_year = data.get('academic_year')
            term = data.get('term')

            if all([student, class_obj, subject, academic_year, term]):
              
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
    def normalise_year(self,year: str) -> str:
  
        year = str(year).replace('/', '-').strip()
        parts = year.split('-')
        
        if len(parts) == 2:
            start = parts[0]         
            end   = parts[1]      
            if len(end) == 2:       
                end = start[:2] + end
            return f"{start}-{end}"
        
        return year 
    
    def _resolve_enrollment(self, obj):
        """Single source of truth for resolving the correct enrollment."""
        class_id    = self.context.get('class_id')
        target_year = self.context.get('academic_year')

        enrollment_qs = obj.enrollments.select_related('class_obj')

        if class_id:
            enrollment_qs = enrollment_qs.filter(class_obj_id=class_id)

        if target_year:
            normalised = self.normalise_year(target_year)
            year_variants = {
                normalised,
                normalised.replace('-', '/'),     
                normalised[:4] + '-' + normalised[-2:],
                normalised[:4] + '/' + normalised[-2:],
            }
            enrollment_qs = enrollment_qs.filter(
                class_obj__academic_year__in=year_variants
            )

        return enrollment_qs.first()


    def get_summary(self, obj):
        enrollment = self._resolve_enrollment(obj)
        if not enrollment: return None
        
        target_year = str(enrollment.class_obj.academic_year).split(' ')[0].replace('/', '-')
        term = obj.academic_grades.filter(academic_year=target_year,class_obj=enrollment.class_obj ).values_list('term', flat=True).first() or "First Term"

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
        enrollment = self._resolve_enrollment(obj)
        if not enrollment:
            return []

        target_year = self.normalise_year(enrollment.class_obj.academic_year)

        class_subjects = enrollment.class_obj.subjects.all()

        year_variants = {
            target_year,
            target_year.replace('-', '/'),          
            target_year[:4] + '-' + target_year[-2:],  
            target_year[:4] + '/' + target_year[-2:],         
        }
        print(year_variants,target_year)

        grades_qs = obj.academic_grades.filter(
            academic_year__in=year_variants,
            class_obj=enrollment.class_obj
        ).select_related('subject', 'student')

        terms = list({g.term for g in grades_qs})

        if not terms:
            return [
                {
                    "id": None,
                    "student": StudentMinimalSerializer(obj).data,
                    "subject": SubjectSerializer(subject).data,
                    "academic_year": target_year,
                    "term": None,
                    "total_score": None,
                    "grade_letter": None,
                    "percentage": None,
                    "subject_rank": None,
                    "class_average": None,
                    "assessment_score": None, "assessment_total": None,
                    "test_score": None,       "test_total": None,
                    "exam_score": None,       "exam_total": None,
                    "weighted_assessment": None,
                    "weighted_test": None,    "weighted_exam": None,
                    "remarks": None,
                }
                for subject in class_subjects
            ]

        grades_by_subject_term = {
            (g.subject_id, g.term): g for g in grades_qs
        }

        s_map   = AcademicReportGenerator.get_subject_ranks_dict(enrollment.class_obj_id, target_year)
        avg_map = AcademicReportGenerator.get_subject_averages(enrollment.class_obj_id, target_year)
        context = {'subject_ranks': s_map, 'subject_averages': avg_map}

        result = []
        for term in terms:                       
            for subject in class_subjects:
                grade = grades_by_subject_term.get((subject.id, term))

                if grade:
                    result.append(GradeSerializer(grade, context=context).data)
                else:
                    result.append({
                        "id": None,
                        "student": StudentMinimalSerializer(obj).data,
                        "subject": SubjectSerializer(subject).data,
                        "academic_year": target_year,
                        "term": term,
                        "total_score": None,
                        "grade_letter": None,
                        "percentage": None,
                        "subject_rank": None,
                        "class_average": avg_map.get((subject.id, term)),
                        "assessment_score": None, "assessment_total": None,
                        "test_score": None,       "test_total": None,
                        "exam_score": None,       "exam_total": None,
                        "weighted_assessment": None,
                        "weighted_test": None,    "weighted_exam": None,
                        "remarks": None,
                    })

        return result

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
        return obj.full_name 

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

def get_subject_ranks(class_id, academic_year_str):
       
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

        return {
            (int(g.student_id), int(g.subject_id), str(g.term)): g.rank 
            for g in grades
        }
