from django.db import transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from apps.students.models import Student
from apps.academic.models import Class, Enrollment
from .models import StudentProgression
from .serializers import (
    StudentProgressionSerializer,
    StudentProgressionUpdateSerializer,
    BulkPromoteSerializer,
)

class StudentProgressionListView(generics.ListAPIView):
    serializer_class = StudentProgressionSerializer
    permission_classes = [IsAdminUser]

    @staticmethod
    def _academic_year_variants(academic_year):
        if not academic_year:
            return []
        raw = str(academic_year).strip()
        if not raw:
            return []
        variants = {raw, raw.replace("/", "-"), raw.replace("-", "/")}
        normalized = raw.replace("/", "-")
        parts = normalized.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = parts
            if len(end) == 2:
                full_end = f"{start[:2]}{end}"
                variants.add(f"{start}-{full_end}")
                variants.add(f"{start}/{full_end}")
            elif len(end) == 4:
                short_end = end[-2:]
                variants.add(f"{start}-{short_end}")
                variants.add(f"{start}/{short_end}")
        return list(variants)

    def get_queryset(self):
        academic_year = self.request.query_params.get('academic_year')
        class_id = self.request.query_params.get('class_id')
        from_class_raw = self.request.query_params.get('from_class')
        status_filter = self.request.query_params.get('status')
        year_variants = self._academic_year_variants(academic_year)

        class_selector = class_id if class_id else from_class_raw
        class_obj = self._resolve_class(class_selector, academic_year) if class_selector else None
        from_class = class_obj.class_name if class_obj else from_class_raw

        qs = StudentProgression.objects.select_related('student', 'updated_by')

        if academic_year:
            qs = qs.filter(academic_year__in=year_variants)
        if from_class:
            qs = qs.filter(from_class=from_class)
        if status_filter:
            qs = qs.filter(status=status_filter)

        if academic_year and from_class and not qs.exists():
            self.initialize_progression_records(academic_year, from_class, class_obj)
            return StudentProgression.objects.filter(
                academic_year__in=year_variants,
                from_class=from_class
            ).select_related('student', 'updated_by')

        return qs

    def _resolve_class(self, from_class_raw, academic_year):
        """
        Accept class id, grade_level, or class_name.
        Prefer class rows within the provided academic year.
        """
        if not from_class_raw:
            return None

        query = Class.objects.all()
        if academic_year:
            query = query.filter(academic_year__in=self._academic_year_variants(academic_year))

        raw = str(from_class_raw).strip()
        if raw.isdigit():
            numeric = int(raw)
            return query.filter(
                Q(id=numeric) | Q(grade_level=numeric) | Q(class_name__iexact=raw)
            ).order_by("id").first()

        return query.filter(class_name__iexact=raw).order_by("id").first()

    def initialize_progression_records(self, academic_year, from_class, class_obj=None):
        """Helper to bulk-create pending records if they don't exist."""
        if not class_obj:
            return

        year_variants = self._academic_year_variants(academic_year)
        students = Student.objects.filter(
            enrollments__class_obj=class_obj,
            enrollments__status=Enrollment.EnrollmentStatus.ACTIVE,
        ).filter(
            Q(enrollments__academic_year__in=year_variants) |
            Q(enrollments__academic_year="", enrollments__class_obj__academic_year__in=year_variants)
        ).distinct()

        with transaction.atomic():
            for student in students:
                progression, created = StudentProgression.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    defaults={
                        'from_class': from_class,
                        'status': 'pending',
                        'updated_by': self.request.user
                    }
                )
                if not created and progression.from_class != from_class:
                    progression.from_class = from_class
                    progression.updated_by = self.request.user
                    progression.save(update_fields=['from_class', 'updated_by'])
class StudentProgressionCreateView(generics.CreateAPIView):
    """
    POST /api/progressions/create/
    Body: { student, academic_year, from_class, to_class, status, remarks }
    """
    serializer_class   = StudentProgressionSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)


class StudentProgressionDetailView(generics.RetrieveUpdateAPIView):
    """
    GET    /api/progressions/<id>/
    PATCH  /api/progressions/<id>/   ← update status / to_class / remarks
    """
    queryset  = StudentProgression.objects.select_related('student', 'updated_by')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return StudentProgressionUpdateSerializer
        return StudentProgressionSerializer

    def perform_update(self, serializer):
        old_status = self.get_object().status
        instance   = serializer.save(updated_by=self.request.user)

        new_status     = instance.status
        final_statuses = {'promoted', 'demoted', 'graduated', 'withheld'}

        if new_status in final_statuses and old_status != new_status:
            try:
                instance.apply_to_enrollment()
            except ValueError as e:
               
                instance.status = old_status
                instance.save(update_fields=['status'])
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'detail': str(e)})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_promote(request):
    serializer = BulkPromoteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    academic_year = data['academic_year']
    from_class = data['from_class']
    to_class = data['to_class']
    exclude_ids = data.get('exclude_ids', [])

    results = {"promoted": 0, "skipped": 0, "errors": []}

    with transaction.atomic():
        progressions = StudentProgression.objects.filter(
            from_class=from_class,
            academic_year=academic_year,
            status='pending'
        ).exclude(student_id__in=exclude_ids)

        for progression in progressions:
            try:
                progression.status = 'promoted'
                progression.to_class = to_class
                progression.updated_by = request.user
                progression.apply_to_enrollment() 
                progression.save()
                results["promoted"] += 1
            except Exception as e:
                results["errors"].append({
                    "student": str(progression.student),
                    "error": str(e)
                })

    return Response(results, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def seed_class_progressions(request):
    """
    POST /api/progressions/seed/
    Body:
    {
        "academic_year": "2024/2025",
        "from_class":    "Class 2"
    }

    Creates a pending progression record for every student
    currently in from_class who doesn't already have one for
    this academic year. Safe to call multiple times.
    """
    academic_year = request.data.get('academic_year')
    from_class_raw = request.data.get('from_class')

    if not academic_year or not from_class_raw:
        return Response(
            {'detail': 'academic_year and from_class are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolver = StudentProgressionListView()
    class_obj = resolver._resolve_class(from_class_raw, academic_year)
    if not class_obj:
        return Response(
            {'detail': f'Class "{from_class_raw}" not found for academic_year "{academic_year}".'},
            status=status.HTTP_404_NOT_FOUND,
        )

    from_class = class_obj.class_name
    year_variants = StudentProgressionListView._academic_year_variants(academic_year)
    students = Student.objects.filter(
        enrollments__class_obj=class_obj,
        enrollments__status=Enrollment.EnrollmentStatus.ACTIVE,
    ).filter(
        Q(enrollments__academic_year__in=year_variants) |
        Q(enrollments__academic_year="", enrollments__class_obj__academic_year__in=year_variants)
    ).distinct()

    created = 0
    skipped = 0

    with transaction.atomic():
        for student in students:
            _, was_created = StudentProgression.objects.get_or_create(
                student=student,
                academic_year=academic_year,
                defaults={
                    'from_class': from_class,
                    'status':     'pending',
                    'updated_by': request.user,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    return Response(
        {
            'detail':  f'{created} record(s) created, {skipped} already existed.',
            'created': created,
            'skipped': skipped,
        },
        status=status.HTTP_201_CREATED,
    )
