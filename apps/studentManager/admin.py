from django.contrib import admin, messages
from django.utils.html import format_html
from .models import StudentProgression

@admin.register(StudentProgression)
class StudentProgressionAdmin(admin.ModelAdmin):

    list_display = (
        'student_info',
        'academic_year',
        'from_class',
        'to_class',
        'status_badge',
        'enrollment_status_badge',
        'updated_by',
    )


    list_filter = (
        'academic_year',
        'from_class',
        'status',
        'enrollment_applied',
    )

    search_fields = (
        'student__first_name', 
        'student__last_name', 
        'student__id',
        'from_class'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'updated_by')

    fieldsets = (
        ("Core Information", {
            "fields": ("student", "academic_year", "status")
        }),
        ("Placement", {
            "fields": ("from_class", "to_class")
        }),
        ("Notes & Audit", {
            "fields": ("remarks", "enrollment_applied", "updated_by", ("created_at", "updated_at"))
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'enrollment_applied', 'updated_by')

    def student_info(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name} ({obj.student.id})"
    student_info.short_description = "Student"

    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',   
            'promoted': '#28a745', 
            'demoted': '#dc3545',   
            'graduated': '#007bff', 
            'withheld': '#ffc107',  
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; text-transform: uppercase; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.status
        )
    status_badge.short_description = "Status"

    def enrollment_status_badge(self, obj):
        if obj.enrollment_applied:
            return "applied"
        return "pending"
    enrollment_status_badge.short_description = "Enrollment Sync"

    def save_model(self, request, obj, form, change):
        """Automatically set the updated_by field to the current admin user."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


    @admin.action(description="Finalize & Apply Transitions to Enrollment")
    def apply_enrollment_transition(self, request, queryset):
        to_process = queryset.filter(enrollment_applied=False).exclude(status='pending')
        
        if not to_process.exists():
            self.message_user(request, "No valid records to apply (must not be 'Pending' or already 'Applied').", messages.WARNING)
            return

        success = 0
        errors = 0

        for record in to_process:
            try:
                record.apply_to_enrollment()
                success += 1
            except Exception as e:
                errors += 1
                self.message_user(request, f"Error for {record.student}: {str(e)}", messages.ERROR)

        self.message_user(
            request, 
            f"Successfully applied {success} transitions. {errors} failed.",
            messages.SUCCESS if errors == 0 else messages.WARNING
        )

    actions = [apply_enrollment_transition]