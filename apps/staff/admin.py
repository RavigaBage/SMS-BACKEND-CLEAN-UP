from django.contrib import admin
from .models import Staff, SalaryStructure, SalaryPayment, StaffAttendance, LeaveRequest,StaffAttendance
from django.utils import timezone

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    # 1. Columns to display in the list view
    list_display = (
        'staff_full_name', 
        'attendance_date', 
        'check_in_time', 
        'check_out_time', 
        'colored_status', 
        'is_late'
    )
    
    # 2. Filters on the right sidebar
    list_filter = ('attendance_date', 'status')
    
    # 3. Search functionality
    search_fields = ('staff__full_name', 'remarks')
    
    # 4. Grouping by date for easier navigation
    date_hierarchy = 'attendance_date'

    # --- CUSTOM COLUMNS ---

    @admin.display(description="Staff Name")
    def staff_full_name(self, obj):
        return obj.staff.full_name

    @admin.display(description="Check In")
    def check_in_time(self, obj):
        return obj.check_in.strftime('%H:%M') if obj.check_in else "-"

    @admin.display(description="Check Out")
    def check_out_time(self, obj):
        return obj.check_out.strftime('%H:%M') if obj.check_out else "-"

    @admin.display(description="Punctuality")
    def is_late(self, obj):
        """Flags if staff arrived after 8:00 AM"""
        if obj.check_in:
            # Assuming 8:00 AM is the cutoff
            if obj.check_in.time() > timezone.datetime.strptime("08:00", "%H:%M").time():
                return "🔴 Late"
            return "🟢 On Time"
        return "-"

    @admin.display(description="Status")
    def colored_status(self, obj):
        from django.utils.html import format_html
        colors = {
            'present': '#10b981',  # Green
            'absent': '#ef4444',   # Red
            'on_leave': '#f59e0b', # Amber
            'half_day': '#3b82f6', # Blue
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )

    # --- BULK ACTIONS ---
    actions = ['mark_as_present']

    @admin.action(description="Mark selected staff as Present")
    def mark_as_present(self, request, queryset):
        queryset.update(
            status='present', 
            check_in=timezone.now().replace(hour=8, minute=0)
        )




class SalaryStructureInline(admin.TabularInline):
    model = SalaryStructure
    extra = 1

class StaffAttendanceInline(admin.TabularInline):
    model = StaffAttendance
    extra = 0
    readonly_fields = ('attendance_date', 'check_in', 'check_out', 'status')
    can_delete = False

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'staff_type', 'specialization', 'email', 'employment_date')
    list_filter = ('staff_type', 'gender', 'employment_date')
    search_fields = ('first_name', 'last_name', 'email', 'national_id')
    inlines = [SalaryStructureInline, StaffAttendanceInline]
    
    fieldsets = (
        ('User Account', {'fields': ('user',)}),
        ('Personal Details', {'fields': (('first_name', 'last_name'), ('date_of_birth', 'gender'), 'photo_url')}),
        ('Contact Info', {'fields': ('phone_number', 'email', 'address')}),
        ('Professional Info', {'fields': ('staff_type', 'specialization', 'employment_date', 'national_id')}),
        ('Medical Info', {'classes': ('collapse',), 'fields': ('health_info',)}),
    )

@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('staff', 'payment_period', 'net_salary', 'status', 'payment_date')
    list_filter = ('status', 'payment_method', 'payment_period')
    search_fields = ('staff__first_name', 'staff__last_name', 'payment_period')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'total_days', 'status')
    list_filter = ('status', 'leave_type')
    actions = ['approve_leave', 'reject_leave']

    def approve_leave(self, request, queryset):
        queryset.update(status='approved', approved_by=request.user)
    approve_leave.short_description = "Mark selected leaves as Approved"