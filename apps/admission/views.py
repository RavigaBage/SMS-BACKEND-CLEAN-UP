from .serializers import AdmissionSerializer
from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsAdminOrHeadmaster
from django.db.models import Q
from .models import Admission


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

                    