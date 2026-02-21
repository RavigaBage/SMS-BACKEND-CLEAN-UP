from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from .models import Student, Parent, StudentParent, ParentInvite
from .email import send_parent_invite_email


# ─── Inlines ──────────────────────────────────────────────────────────────────

class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    autocomplete_fields = ['parent']
    verbose_name = "Parent / Guardian"
    verbose_name_plural = "Parents / Guardians"


class StudentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    autocomplete_fields = ['student']
    verbose_name = "Linked Ward"
    verbose_name_plural = "Linked Wards"


class ParentInviteInline(admin.TabularInline):
    model = ParentInvite
    extra = 0
    can_delete = False
    readonly_fields = ['code', 'status_badge', 'expires_at', 'used_at', 'created_by', 'created_at']
    fields = ['code', 'status_badge', 'expires_at', 'used_at', 'created_by', 'created_at']
    verbose_name = "Invite Code"
    verbose_name_plural = "Invite Codes"

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.used:
            return mark_safe('<span style="background:#6c757d;color:white;padding:2px 8px;border-radius:4px;">Used</span>')
        if obj.is_expired:
            return mark_safe('<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:4px;">Expired</span>')
        return mark_safe('<span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-weight:bold;">Active ✓</span>')

    def has_add_permission(self, request, obj=None):
        return False


# ─── Student Admin ────────────────────────────────────────────────────────────

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display    = ('admission_number', 'get_photo', 'full_name', 'gender', 'status_badge', 'age')
    list_filter     = ('status', 'gender', 'admission_date')
    search_fields   = ('admission_number', 'first_name', 'last_name', 'middle_name')
    readonly_fields = ('age', 'created_at', 'updated_at', 'get_photo_large')
    inlines         = [StudentParentInline]
    list_per_page   = 25

    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
                ('admission_number', 'status'),
                ('date_of_birth', 'gender', 'age'),
            )
        }),
        ('Academic Details', {
            'fields': ('admission_date', 'class_obj', 'photo_url', 'get_photo_large')
        }),
        ('Medical & Personal Info', {
            'classes': ('collapse',),
            'fields': ('blood_group', 'medical_conditions', 'religion', 'nationality', 'address')
        }),
        ('System Info', {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    @admin.display(description='Photo')
    def get_photo(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="width:45px;height:45px;border-radius:50%;object-fit:cover;" />',
                obj.photo_url
            )
        return mark_safe(
            '<div style="width:45px;height:45px;border-radius:50%;background:#e2e8f0;'
            'display:flex;align-items:center;justify-content:center;font-size:18px;">👤</div>'
        )

    @admin.display(description='Photo Preview')
    def get_photo_large(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="max-width:200px;border-radius:10px;" />', obj.photo_url)
        return "No photo uploaded."

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'active':      ('#28a745', 'Active'),
            'graduated':   ('#17a2b8', 'Graduated'),
            'suspended':   ('#dc3545', 'Suspended'),
            'transferred': ('#ffc107', 'Transferred'),
            'withdrawn':   ('#6c757d', 'Withdrawn'),
        }
        color, label = colors.get(obj.status, ('#6c757d', obj.status.title()))
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, label
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ─── Parent Admin ─────────────────────────────────────────────────────────────

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'relationship', 'phone_number', 'email',
        'ward_count', 'app_access_badge', 'active_invite_code',
    )
    list_filter         = ('relationship', 'created_at')
    search_fields       = ('first_name', 'last_name', 'phone_number', 'email', 'national_id')
    ordering            = ('last_name', 'first_name')
    list_per_page       = 25
    readonly_fields     = ('created_at', 'updated_at', 'current_invite_code')
    autocomplete_fields = ['user']
    inlines             = [StudentInline, ParentInviteInline]
    actions             = ['generate_and_email_invite_codes', 'revoke_app_access']

    fieldsets = (
        ('Personal Information', {
            'fields': (('first_name', 'last_name'), 'relationship', 'national_id')
        }),
        ('Contact', {
            'fields': (('phone_number', 'email'), 'address')
        }),
        ('Employment', {
            'classes': ('collapse',),
            'fields': ('occupation', 'workplace')
        }),
        ('App Access', {
            'fields': ('user', 'current_invite_code'),
            'description': (
                '💡 To send an invite: go back to the Parents list, select this parent, '
                'then choose "Generate & email invite" from the Actions dropdown.'
            )
        }),
        ('Metadata', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    # ── List display methods ──────────────────────────────────────────────────

    @admin.display(description='Wards')
    def ward_count(self, obj):
        count = obj.student_links.count()
        color = '#28a745' if count > 0 else '#6c757d'
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;'
            'border-radius:4px;font-weight:bold;">{}</span>',
            color, count
        )

    @admin.display(description='App Access')
    def app_access_badge(self, obj):
        if obj.user_id:
            return mark_safe(
                '<span style="background:#28a745;color:white;padding:3px 10px;'
                'border-radius:4px;font-weight:bold;">✓ Active</span>'
            )
        return mark_safe(
            '<span style="background:#ffc107;color:#333;padding:3px 10px;'
            'border-radius:4px;font-weight:bold;">✗ No Access</span>'
        )

    @admin.display(description='Invite Code')
    def active_invite_code(self, obj):
        invite = obj.invites.filter(used=False).order_by('-created_at').first()
        if not invite:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        if invite.is_expired:
            return mark_safe(
                '<span style="background:#dc3545;color:white;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Expired</span>'
            )
        return format_html(
            '<code style="background:#f1f5f9;padding:3px 10px;border-radius:4px;'
            'font-weight:bold;letter-spacing:2px;font-size:13px;">{}</code>',
            invite.code
        )

    @admin.display(description='Current Invite Code')
    def current_invite_code(self, obj):
        """Shown on the Parent detail page — large and easy to copy if needed."""
        invite = obj.invites.filter(used=False).order_by('-created_at').first()
        if not invite:
            return mark_safe(
                '<span style="color:#94a3b8;">'
                'No active code. Go to the Parents list, select this parent, '
                'and run "Generate &amp; email invite" from the Actions menu.'
                '</span>'
            )
        if invite.is_expired:
            return mark_safe(
                '<span style="color:#dc3545;">'
                'Last code expired. Generate a new one from the Actions menu.'
                '</span>'
            )
        return format_html(
            '<div style="margin-bottom:8px;">'
            '<code style="font-size:24px;letter-spacing:6px;font-weight:900;'
            'background:#f1f5f9;padding:10px 20px;border-radius:8px;'
            'border:2px dashed #2d52c4;color:#1f3889;">{}</code>'
            '</div>'
            '<p style="margin:6px 0 0;color:#64748b;font-size:12px;">'
            '📧 Emailed to <strong>{}</strong> &nbsp;|&nbsp; '
            '⏰ Expires <strong>{}</strong>'
            '</p>',
            invite.code,
            obj.email or '(no email on file)',
            invite.expires_at.strftime('%d %b %Y, %H:%M'),
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @admin.action(description='📧 Generate & email invite code(s) to selected parents')
    def generate_and_email_invite_codes(self, request, queryset):
        emailed = []
        skipped = []
        failed  = []

        for parent in queryset:
            # Already has app access — skip
            if parent.user_id:
                skipped.append(f"{parent.full_name} (already has access)")
                continue

            # No email address — can't send
            if not parent.email:
                skipped.append(f"{parent.full_name} (no email on file)")
                continue

            # Create the invite code
            invite = ParentInvite.objects.create(
                parent=parent,
                created_by=request.user,
            )

            # Send the email
            success, error = send_parent_invite_email(invite)

            if success:
                emailed.append(parent.full_name)
            else:
                # Code exists but email failed — admin can still share it manually
                failed.append(f"{parent.full_name} (email failed: {error})")

        if emailed:
            self.message_user(
                request,
                f"✅ Invite emailed to {len(emailed)} parent(s): {', '.join(emailed)}.",
                level='success',
            )
        if skipped:
            self.message_user(
                request,
                f"⏭️ {len(skipped)} skipped: {'; '.join(skipped)}.",
                level='warning',
            )
        if failed:
            self.message_user(
                request,
                f"❌ Email failed for {len(failed)}: {'; '.join(failed)}. "
                f"The codes were still created — share them manually from the parent detail page.",
                level='error',
            )

    @admin.action(description='🔒 Revoke app access for selected parents')
    def revoke_app_access(self, request, queryset):
        revoked = 0
        for parent in queryset:
            if parent.user:
                parent.user.is_active = False
                parent.user.save(update_fields=['is_active'])
                revoked += 1
        self.message_user(
            request,
            f'{revoked} parent account(s) deactivated.' if revoked else 'No active accounts found.',
            level='warning' if revoked else 'error',
        )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .prefetch_related('student_links', 'invites')
            .select_related('user')
        )


# ─── StudentParent Admin ──────────────────────────────────────────────────────

@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display  = ('student', 'parent', 'is_primary_contact', 'can_pickup')
    list_filter   = ('is_primary_contact', 'can_pickup')
    search_fields = (
        'student__first_name', 'student__last_name',
        'parent__first_name',  'parent__last_name',
    )


# ─── ParentInvite Admin ───────────────────────────────────────────────────────

@admin.register(ParentInvite)
class ParentInviteAdmin(admin.ModelAdmin):
    list_display    = ('code_display', 'parent_link', 'status_badge', 'expires_at', 'used_at', 'created_by', 'created_at')
    list_filter     = ('used', 'created_at')
    search_fields   = ('code', 'parent__first_name', 'parent__last_name', 'parent__email')
    readonly_fields = ('code', 'used', 'used_at', 'created_at', 'created_by')
    ordering        = ('-created_at',)

    @admin.display(description='Code')
    def code_display(self, obj):
        return format_html(
            '<code style="background:#f1f5f9;padding:3px 10px;border-radius:4px;'
            'font-weight:bold;letter-spacing:2px;">{}</code>',
            obj.code
        )

    @admin.display(description='Parent')
    def parent_link(self, obj):
        url = reverse('admin:students_parent_change', args=[obj.parent.pk])
        return format_html('<a href="{}">{}</a>', url, obj.parent.full_name)

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.used:
            return mark_safe('<span style="background:#6c757d;color:white;padding:3px 10px;border-radius:4px;">Used</span>')
        if obj.is_expired:
            return mark_safe('<span style="background:#dc3545;color:white;padding:3px 10px;border-radius:4px;">Expired</span>')
        return mark_safe('<span style="background:#28a745;color:white;padding:3px 10px;border-radius:4px;font-weight:bold;">Active</span>')

    def has_add_permission(self, request):
        return False