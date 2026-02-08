from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'specialization')
    search_fields = ('first_name', 'last_name', 'user__username', 'specialization')
    ordering = ('last_name', 'first_name')

