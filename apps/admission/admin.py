from django.contrib import admin
from .models import Admission


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'surname',
        'first_name',
        'gender',
        'religion',
        'has_normal_health',
        'has_normal_hearing',
        'has_psychological_trauma',
        'created_at',
    )

    list_filter = (
        'gender',
        'religion',
        'has_normal_health',
        'has_normal_hearing',
        'has_psychological_trauma',
        'mother_status',
        'father_status',
        'created_at',
    )

    search_fields = (
        'first_name',
        'surname',
        'fees_payer_name',
        'male_guardian_name',
        'female_guardian_name',
        'admission_number',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ("Applicant Personal Information", {
            'fields': (
                'surname',
                'first_name',
                'middle_name',
                'date_of_birth',
                'gender',
                'religion',
            )
        }),

        ("Medical Information", {
            'fields': (
                'has_normal_health',
                'health_condition_details',
                'has_normal_hearing',
                'hearing_condition_details',
                'other_health_information',
            )
        }),

        ("Psychological Wellbeing", {
            'fields': (
                'adjustment_and_cooperation',
                'attitude_description',
                'has_psychological_trauma',
                'psychological_trauma_details',
            )
        }),

        ("Parents Information", {
            'fields': (
                'mother_status',
                'father_status',
                'parents_relationship_status',
            )
        }),

        ("Fees Payer", {
            'fields': (
                'fees_payer_title',
                'fees_payer_name',
                'fees_payer_address',
                'fees_payer_phone',
                'fees_payer_email',
                'fees_payer_relationship',
            )
        }),

        ("Office Use Only", {
            'fields': (
                'admission_number',
                'admission_date',
                'office_in_charge_name',
                'office_signature',
                'office_date',
            )
        }),

        ("System Info", {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    list_select_related = False

    ordering = ('-created_at',)

   

    # -------------------------
    actions = ['mark_as_reviewed']

    def mark_as_reviewed(self, request, queryset):
        queryset.update(admission_number="REVIEWED")
    mark_as_reviewed.short_description = "Mark selected admissions as reviewed"