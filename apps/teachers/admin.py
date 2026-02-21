from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """
    Django Admin configuration for Teacher model
    Provides comprehensive management interface for teachers
    """
    
    # List display configuration
    list_display = [
        'id',
        'full_name_link',
        'user_link',
        'specialization',
        'subject_count',
        'years_of_experience',
        'is_active_badge',
        'assigned_by_link',
        'date_joined'
    ]
    
    # List filters
    list_filter = [
        'is_active',
        'specialization',
        'years_of_experience',
        'date_joined',
        'subjects'
    ]
    
    # Search fields
    search_fields = [
        'first_name',
        'last_name',
        'user__username',
        'user__email',
        'specialization',
        'phone_number'
    ]
    
    # Ordering
    ordering = ['-date_joined', 'last_name', 'first_name']
    
    # Fields to display in detail view
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'first_name',
                'last_name',
                'is_active'
            )
        }),
        ('Teaching Information', {
            'fields': (
                'specialization',
                'subjects',
                'qualifications',
                'years_of_experience'
            ),
            'description': 'Teaching-specific information and qualifications'
        }),
        ('Contact Information', {
            'fields': (
                'phone_number',
                'emergency_contact'
            )
        }),
        ('Metadata', {
            'fields': (
                'assigned_by',
                'date_joined',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Read-only fields
    readonly_fields = [
        'date_joined',
        'created_at',
        'updated_at'
    ]
    
    # Filter horizontal for many-to-many fields
    filter_horizontal = ['subjects']
    
    # Autocomplete fields
    autocomplete_fields = ['user', 'assigned_by']
    
    # Items per page
    list_per_page = 25
    
    # Enable actions
    actions = [
        'activate_teachers',
        'deactivate_teachers',
        'export_teachers_csv'
    ]
    
    # ─── Custom list display methods ──────────────────────────────────────────

    @admin.display(description='Teacher Name', ordering='last_name')
    def full_name_link(self, obj):
        """Display full name as clickable link"""
        url = reverse('admin:teachers_teacher_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.full_name)

    @admin.display(description='User Account', ordering='user__username')
    def user_link(self, obj):
        """Display user as clickable link"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}" style="color: #447e9b;">{}</a>',
                url,
                obj.user.username
            )
        return '-'

    @admin.display(description='Subjects')
    def subject_count(self, obj):
        """Display count of assigned subjects as a coloured badge"""
        count = obj.subjects.count()
        color = '#28a745' if count > 0 else '#6c757d'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px;">{}</span>',
            color,
            count,
        )

    # ✅ FIX: removed boolean=True — this method returns HTML, not True/False/None.
    #    boolean=True tells Django to render the return value as a tick/cross icon,
    #    which requires the value to be exactly True, False, or None. Passing an
    #    HTML string caused the KeyError seen in the traceback.
    @admin.display(description='Status', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            color, label = '#28a745', 'Active'
        else:
            color, label = '#dc3545', 'Inactive'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, label   # ← these are the required args
        )

    @admin.display(description='Assigned By', ordering='assigned_by__username')
    def assigned_by_link(self, obj):
        """Display assigned_by user as clickable link"""
        if obj.assigned_by:
            url = reverse('admin:accounts_user_change', args=[obj.assigned_by.pk])
            return format_html(
                '<a href="{}" style="color: #447e9b;">{}</a>',
                url,
                obj.assigned_by.username
            )
        return '-'

    # ─── Custom actions ───────────────────────────────────────────────────────

    @admin.action(description='✓ Activate selected teachers')
    def activate_teachers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} teacher(s) activated successfully.', level='success')

    @admin.action(description='✗ Deactivate selected teachers')
    def deactivate_teachers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} teacher(s) deactivated successfully.', level='warning')

    @admin.action(description='📥 Export to CSV')
    def export_teachers_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from datetime import datetime

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="teachers_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Username', 'Email',
            'Specialization', 'Subjects', 'Qualifications', 'Years of Experience',
            'Phone Number', 'Emergency Contact', 'Status', 'Date Joined', 'Assigned By'
        ])

        for teacher in queryset.select_related('user', 'assigned_by').prefetch_related('subjects'):
            writer.writerow([
                teacher.id,
                teacher.first_name,
                teacher.last_name,
                teacher.user.username if teacher.user else '',
                teacher.user.email if teacher.user else '',
                teacher.specialization,
                teacher.subject_list,
                teacher.qualifications,
                teacher.years_of_experience,
                teacher.phone_number,
                teacher.emergency_contact,
                'Active' if teacher.is_active else 'Inactive',
                teacher.date_joined.strftime('%Y-%m-%d') if teacher.date_joined else '',
                teacher.assigned_by.username if teacher.assigned_by else ''
            ])

        self.message_user(
            request,
            f'{queryset.count()} teacher(s) exported to CSV successfully.',
            level='success'
        )
        return response

    # ─── Queryset optimisation ────────────────────────────────────────────────

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset
            .select_related('user', 'assigned_by')
            .prefetch_related('subjects')
            .annotate(subject_count=Count('subjects'))
        )

    # ─── Save / form hooks ────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        if not change and not obj.assigned_by:
            obj.assigned_by = request.user

        if obj.user:
            if not obj.first_name and obj.user.first_name:
                obj.first_name = obj.user.first_name
            if not obj.last_name and obj.user.last_name:
                obj.last_name = obj.user.last_name

        super().save_model(request, obj, form, change)
        action = 'updated' if change else 'created'
        self.message_user(request, f'Teacher "{obj.full_name}" {action} successfully.', level='success')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'user' in form.base_fields:
            form.base_fields['user'].help_text = 'Select a user with "Teacher" role'
        return form

    # ─── Custom URLs ──────────────────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path
        custom_urls = [
            path(
                '<int:teacher_id>/workload/',
                self.admin_site.admin_view(self.teacher_workload_view),
                name='teacher_workload'
            ),
        ]
        return custom_urls + super().get_urls()

    def teacher_workload_view(self, request, teacher_id):
        from django.shortcuts import render, get_object_or_404
        teacher = get_object_or_404(Teacher, pk=teacher_id)
        context = {
            'teacher': teacher,
            'assigned_classes': teacher.get_assigned_classes(),
            'subject_assignments': teacher.get_subject_assignments(),
            'total_workload': (
                teacher.get_assigned_classes().count()
                + teacher.get_subject_assignments().count()
            ),
            'title': f'Workload - {teacher.full_name}',
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        }
        return render(request, 'admin/teacher_workload.html', context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        teacher = self.get_object(request, object_id)
        if teacher:
            extra_context['assigned_classes_count'] = teacher.get_assigned_classes().count()
            extra_context['subject_assignments_count'] = teacher.get_subject_assignments().count()
            extra_context['show_workload_link'] = True
        return super().change_view(request, object_id, form_url, extra_context)


# ─── Optional inline for User admin ──────────────────────────────────────────

class TeacherInline(admin.StackedInline):
    """Inline admin for Teacher in User admin"""
    model = Teacher
    can_delete = False
    verbose_name = 'Teacher Profile'
    verbose_name_plural = 'Teacher Profile'

    fieldsets = (
        ('Teaching Information', {
            'fields': (
                'first_name', 'last_name', 'specialization', 'subjects',
                'qualifications', 'years_of_experience',
                'phone_number', 'emergency_contact', 'is_active'
            )
        }),
    )

    filter_horizontal = ['subjects']

    def has_add_permission(self, request, obj=None):
        if obj and obj.role == 'teacher' and not hasattr(obj, 'teacher_profile'):
            return True
        return False

