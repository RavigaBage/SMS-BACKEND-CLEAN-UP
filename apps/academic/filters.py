from django_filters import rest_framework as filters
from apps.academic.models import Grade, Class, Enrollment



class ClassFilter(filters.FilterSet):
    """Advanced filtering for classes"""
    class_name = filters.CharFilter(lookup_expr='icontains')
    academic_year = filters.CharFilter(lookup_expr='exact')
    has_teacher = filters.NumberFilter(field_name='teachers', lookup_expr='isnull', exclude=True)
    min_students = filters.NumberFilter(method='filter_min_students')
    max_students = filters.NumberFilter(method='filter_max_students')
    
    class Meta:
        model = Class
        fields = ['class_name', 'academic_year']
    
    def filter_min_students(self, queryset, name, value):
        return queryset.annotate(
            student_count=filters.Count('enrollments')
        ).filter(student_count__gte=value)
    
    def filter_max_students(self, queryset, name, value):
        return queryset.annotate(
            student_count=filters.Count('enrollments')
        ).filter(student_count__lte=value)


class EnrollmentFilter(filters.FilterSet):
    """Advanced filtering for enrollments"""
    student_status = filters.CharFilter(field_name='student__status')
    class_year = filters.CharFilter(field_name='class_obj__academic_year')
    
    class Meta:
        model = Enrollment
        fields = ['student', 'class_obj', 'student_status', 'class_year']
