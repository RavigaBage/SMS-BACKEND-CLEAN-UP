from django.contrib import admin
from .models import Subject, Class, Enrollment,AcademicYear

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_name', 'subject_code')
    search_fields = ('subject_name', 'subject_code')


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('class_name', 'academic_year', 'class_teacher')
    list_filter = ('academic_year',)
    search_fields = ('class_name', 'teacher__user__username')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_obj')
    list_filter = ('class_obj',)
    search_fields = ('student__user__username',)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('year_name', 'start_date', 'end_date', 'is_current')
    list_editable = ('is_current',) # Quickly toggle the current year from the list view
    list_filter = ('is_current',)