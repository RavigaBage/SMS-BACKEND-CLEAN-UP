from django.contrib import admin
from .models import Timetable, Syllabus

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('class_obj', 'subject', 'teacher', 'day_of_week', 'start_time', 'end_time', 'room_number')
    list_filter = ('day_of_week', 'class_obj', 'teacher')
    search_fields = ('class_obj__class_name', 'subject__subject_name', 'teacher__user__username', 'room_number')
    ordering = ('class_obj', 'day_of_week', 'start_time')


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ('week_number', 'subject', 'teacher', 'topic_title')
    list_filter = ('subject', 'teacher')
    search_fields = ('topic_title', 'subject__subject_name', 'teacher__user__username')
    ordering = ('subject', 'week_number')

