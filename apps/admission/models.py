from django.db import models
from django.core.validators import RegexValidator


class Admission(models.Model):

 
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    PARENT_STATUS_CHOICES = [
        ('alive', 'Alive'),
        ('deceased', 'Deceased'),
        ('unknown', 'Unknown'),
    ]

    FAMILY_STATUS_CHOICES = [
        ('living_together', 'Living Together'),
        ('separated', 'Separated'),
        ('divorced', 'Divorced'),
    ]

    TITLE_CHOICES = [
        ('mr', 'Mr'),
        ('mrs', 'Mrs'),
        ('dr', 'Dr'),
        ('prof', 'Prof'),
    ]


    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100)

    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    religion = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    mother_status = models.CharField(
        max_length=20,
        choices=PARENT_STATUS_CHOICES,
        default='alive'
    )

    father_status = models.CharField(
        max_length=20,
        choices=PARENT_STATUS_CHOICES,
        default='alive'
    )

    parents_relationship_status = models.CharField(
        max_length=30,
        choices=FAMILY_STATUS_CHOICES,
        blank=True,
        null=True
    )

    fees_payer_title = models.CharField(
        max_length=10,
        choices=TITLE_CHOICES,
        blank=True,
        null=True
    )

    fees_payer_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    fees_payer_address = models.TextField(
        blank=True,
        null=True
    )

    fees_payer_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    fees_payer_email = models.EmailField(
        blank=True,
        null=True
    )

    fees_payer_relationship = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )


    male_guardian_title = models.CharField(
        max_length=10,
        choices=TITLE_CHOICES,
        blank=True,
        null=True
    )

    male_guardian_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    male_guardian_occupation = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    male_guardian_address = models.TextField(
        blank=True,
        null=True
    )

    male_guardian_relationship = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    male_guardian_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )


    female_guardian_title = models.CharField(
        max_length=10,
        choices=TITLE_CHOICES,
        blank=True,
        null=True
    )

    female_guardian_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    female_guardian_occupation = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    female_guardian_address = models.TextField(
        blank=True,
        null=True
    )

    female_guardian_relationship = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    female_guardian_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    has_normal_health = models.BooleanField(default=True)

    health_condition_details = models.TextField(
        blank=True,
        null=True
    )

    has_normal_hearing = models.BooleanField(default=True)

    hearing_condition_details = models.TextField(
        blank=True,
        null=True
    )

    other_health_information = models.TextField(
        blank=True,
        null=True
    )


    adjustment_and_cooperation = models.TextField(
        blank=True,
        null=True
    )

    attitude_description = models.TextField(
        blank=True,
        null=True
    )

    has_psychological_trauma = models.BooleanField(
        default=False
    )

    psychological_trauma_details = models.TextField(
        blank=True,
        null=True
    )

    admission_date = models.DateField(
        blank=True,
        null=True
    )

    admission_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    office_in_charge_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='admin'
    )

    office_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='admin'
    )

    office_date = models.DateField(
        blank=True,
        null=True
    )

    approval = models.BooleanField(
        blank=True,
        default=False
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return f"{self.surname} {self.first_name}"

    @property
    def full_name(self):
        return f"{self.surname} {self.middle_name or ''} {self.first_name}"

    @property
    def applicant_age(self):

        from datetime import date

        today = date.today()

        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (
                    self.date_of_birth.month,
                    self.date_of_birth.day
                )
            )
        )

    class Meta:
        db_table = 'admission'
        ordering = ['-created_at']
        verbose_name = "Admission"
        verbose_name_plural = "Admissions"