from rest_framework import viewsets
from apps.teachers.models import Teacher
from apps.teachers.serializers import TeacherSerializer
from apps.academic.serializers import SubjectSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def subjects(self, request, pk=None):
        # prefetch_related reduces the number of database hits
        teacher = self.get_queryset().prefetch_related('subjects').get(pk=pk)
        subjects = teacher.subjects.all() 
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)

