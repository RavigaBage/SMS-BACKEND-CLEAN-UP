from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User model for staff AND parent authentication.
    Students do NOT have user accounts.
    """

    class Role(models.TextChoices):
        ADMIN       = 'admin',       _('Admin')
        HEADMASTER  = 'headmaster',  _('Headmaster')
        BURSAR      = 'bursar',      _('Bursar')
        TEACHER     = 'teacher',     _('Teacher')
        PARENT      = 'parent',      _('Parent')   # ← added

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text=_('User role determines access permissions')
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        help_text=_('User who created this account')
    )
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        permission_map = {
            self.Role.ADMIN:      ['all'],
            self.Role.HEADMASTER: ['all'],
            self.Role.BURSAR:     ['finance', 'students', 'reports'],
            self.Role.TEACHER:    ['students', 'grades', 'attendance'],
            self.Role.PARENT:     ['own_children'],  
        }
        user_permissions = permission_map.get(self.role, [])
        return 'all' in user_permissions or permission in user_permissions