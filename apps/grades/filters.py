from django_filters import rest_framework as filters
from apps.grades.models import Grade


class GradeFilter(filters.FilterSet):
    """Advanced filtering for grades"""
    student_id = filters.NumberFilter(field_name='student__id')
    student_name = filters.CharFilter(field_name='student__first_name', lookup_expr='icontains')
    class_name = filters.CharFilter(field_name='class_obj__class_name', lookup_expr='icontains')
    subject_name = filters.CharFilter(field_name='subject__subject_name', lookup_expr='icontains')
    min_score = filters.NumberFilter(field_name='total_score', lookup_expr='gte')
    max_score = filters.NumberFilter(field_name='total_score', lookup_expr='lte')
    grade_letter = filters.CharFilter(field_name='grade_letter', lookup_expr='iexact')
    date_from = filters.DateFilter(field_name='grade_date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='grade_date', lookup_expr='lte')
    
    class Meta:
        model = Grade
        fields = [
            'student', 'class_obj', 'subject', 
            'academic_year', 'term', 'grade_letter'
        ]

