from django.contrib import admin
from .models import Grade
# Register your models here.

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'class_obj', 'total_score', 'marks', 'grade_letter', 'grade_date')
    list_filter = ('grade_date', 'subject')
    search_fields = ('student__user__username', 'subject__subject_name')

    def marks(self, obj):
        return f"{obj.assessment_score}/{obj.assessment_total} | {obj.test_score}/{obj.test_total} | {obj.exam_score}/{obj.exam_total}"
    marks.short_description = 'Marks Breakdown'
