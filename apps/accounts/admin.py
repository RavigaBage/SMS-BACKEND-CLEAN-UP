from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin following your specific User model fields.
    """
    # 1. Fields to display in the list view
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    
    # 2. Fieldsets: This is where your error was happening. 
    # We must only include fields that exist in your model.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Role & Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Audit Info'), {'fields': ('created_by', 'last_login', 'date_joined')}),
    )

    # 3. Fields for the "Add User" form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {
            'classes': ('wide',),
            'fields': ('role', 'email', 'first_name', 'last_name'),
        }),
    )

    readonly_fields = ('date_joined', 'last_login')

    # Automatically set 'created_by' when saving via Admin
    def save_model(self, request, obj, form, change):
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)