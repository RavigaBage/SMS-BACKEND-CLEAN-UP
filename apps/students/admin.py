from django.contrib import admin
from django.utils.html import format_html
from .models import Student, Parent, StudentParent

# --- INLINES ---

class StudentParentInline(admin.TabularInline):
    """Allows adding parents directly on the Student admin page."""
    model = StudentParent
    extra = 1
    autocomplete_fields = ['parent']  # Requires SearchFields in ParentAdmin

class StudentInline(admin.TabularInline):
    """Allows adding students directly on the Parent admin page."""
    model = StudentParent
    extra = 1
    autocomplete_fields = ['student'] # Requires SearchFields in StudentAdmin

# --- ADMIN VIEWS ---

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # List View configuration
    list_display = ('admission_number', 'get_photo', 'full_name', 'gender', 'status', 'age')
    list_filter = ('status', 'gender', 'admission_date')
    search_fields = ('admission_number', 'first_name', 'last_name', 'middle_name')
    readonly_fields = ('age', 'created_at', 'updated_at', 'get_photo_large')
    inlines = [StudentParentInline]
    
    # Detail View grouping
    fieldsets = (
        ('Basic Information', {
            'fields': (('first_name', 'middle_name', 'last_name'), ('admission_number', 'status'), ('date_of_birth', 'gender', 'age'))
        }),
        ('Academic Details', {
            'fields': ('admission_date', 'photo_url', 'get_photo_large')
        }),
        ('Medical & Personal Info', {
            'classes': ('collapse',),
            'fields': ('blood_group', 'medical_conditions', 'religion', 'nationality', 'address')
        }),
        ('System Info', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def get_photo(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="width: 45px; height:45px; border-radius: 50%;" />', obj.photo_url)
        return "No Photo"
    get_photo.short_description = 'Photo'

    def get_photo_large(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="max-width: 200px; border-radius: 10px;" />', obj.photo_url)
        return "No Photo uploaded"
    get_photo_large.short_description = 'Current Photo'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'relationship', 'phone_number', 'email', 'occupation')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email', 'national_id')
    list_filter = ('relationship',)
    inlines = [StudentInline]
    
    fieldsets = (
        ('Contact Information', {
            'fields': (('first_name', 'last_name'), ('phone_number', 'email'), 'address')
        }),
        ('Professional & ID', {
            'fields': ('relationship', 'occupation', 'workplace', 'national_id')
        }),
    )

# Optional: Register the relationship table separately if you want to filter by "Primary Contact"
@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent', 'is_primary_contact', 'can_pickup')
    list_filter = ('is_primary_contact', 'can_pickup')
    search_fields = ('student__first_name', 'student__last_name', 'parent__first_name', 'parent__last_name')