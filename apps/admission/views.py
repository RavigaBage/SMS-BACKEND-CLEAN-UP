from datetime import date
from .serializers import AdmissionSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from apps.accounts.permissions import IsAdminOrHeadmaster
from django.db.models import Q
from .models import Admission
from apps.students.services import StudentService
import logging

logger = logging.getLogger(__name__)


class AdmissionViewset(viewsets.ModelViewSet):

    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadmaster]
    queryset = Admission.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            return []
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()

        religion = self.request.query_params.get('religion', None)
        if religion:
            queryset = queryset.filter(religion=religion)

        gender = self.request.query_params.get('gender', None)
        if gender:
            queryset = queryset.filter(gender=gender)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(surname__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            admission = self.get_object()
            admission.approval = True
            admission.save(update_fields=['approval'])
            return Response(
                {"message": "Admission approved.", "approval": True},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error approving admission {pk}: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        try:
            admission = self.get_object()

            class_id = request.data.get("class_id")
            if not class_id:
                return Response(
                    {"error": "class_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                class_id = int(class_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": f"Invalid class_id: '{class_id}'. Must be a number."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if getattr(admission, 'enrolled', False):
                return Response(
                    {"error": "This applicant has already been enrolled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            student_data = {
                'admission_number': admission.admission_number or f"ADM-{admission.id:04d}",
                'first_name': admission.first_name,
                'last_name': admission.surname,
                'middle_name': admission.middle_name or '',
                'date_of_birth': admission.date_of_birth,
                'gender': admission.gender,
                'address': '',
                'nationality': '',
                'religion': admission.religion or '',
                'blood_group': '',
                'medical_conditions': '',
                'admission_date': admission.admission_date or date.today(),
                'photo_url': '',
            }

            # Build parent data from admission guardian fields
            parent_data_list = []

            if admission.fees_payer_name:
                parent_data_list.append({
                    'first_name': admission.fees_payer_name.split()[0] if admission.fees_payer_name else '',
                    'last_name': ' '.join(admission.fees_payer_name.split()[1:]) if admission.fees_payer_name else '',
                    'phone_number': admission.fees_payer_phone or '',
                    'email': admission.fees_payer_email or '',
                    'relationship': admission.fees_payer_relationship or 'guardian',
                })

            if admission.male_guardian_name:
                parent_data_list.append({
                    'first_name': admission.male_guardian_name.split()[0],
                    'last_name': ' '.join(admission.male_guardian_name.split()[1:]),
                    'phone_number': admission.male_guardian_phone or '',
                    'email': '',
                    'relationship': admission.male_guardian_relationship or 'father',
                })

            if admission.female_guardian_name:
                parent_data_list.append({
                    'first_name': admission.female_guardian_name.split()[0],
                    'last_name': ' '.join(admission.female_guardian_name.split()[1:]),
                    'phone_number': admission.female_guardian_phone or '',
                    'email': '',
                    'relationship': admission.female_guardian_relationship or 'mother',
                })

            # Register the student via StudentService
            service = StudentService()
            result = service.register_student(
                student_data=student_data,
                parent_data_list=parent_data_list,
                class_id=class_id,
                created_by=request.user
            )

            # Mark admission as enrolled so it can't be enrolled twice
            admission.approval = True
            admission.enrolled = True  # add this BooleanField to your Admission model
            admission.save(update_fields=['approval', 'enrolled'])

            return Response(
                {
                    "message": "Student enrolled successfully.",
                    "student_id": result['student'].id,
                    "admission_number": result['student'].admission_number,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error enrolling admission {pk}: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )