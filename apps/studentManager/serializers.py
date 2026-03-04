from rest_framework import serializers
from .models import StudentProgression

class StudentProgressionSerializer(serializers.ModelSerializer):
    """Full serializer — used for retrieve / update."""

    student_name  = serializers.CharField(source='student.__str__', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model  = StudentProgression
        fields = [
            'id',
            'student',
            'student_name',
            'academic_year',
            'from_class',
            'to_class',
            'status',
            'remarks',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['updated_by', 'created_at', 'updated_at']


class StudentProgressionUpdateSerializer(serializers.ModelSerializer):
    """Lightweight serializer for single-student status updates."""

    class Meta:
        model  = StudentProgression
        fields = ['status', 'to_class', 'remarks']

    def validate(self, data):
        status = data.get('status', getattr(self.instance, 'status', None))
        to_class = data.get('to_class', getattr(self.instance, 'to_class', None))

        if status in ('promoted', 'demoted'):
            if not to_class or str(to_class).strip() == "":
                raise serializers.ValidationError(
                    {'to_class': f'A destination class is required when status is {status}.'}
                )
        return data


class BulkPromoteSerializer(serializers.Serializer):
    """Payload for bulk promotion of an entire class."""

    academic_year = serializers.CharField(max_length=20)
    from_class    = serializers.CharField(max_length=50)
    to_class      = serializers.CharField(max_length=50)
    exclude_ids   = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="Student IDs to exclude from the bulk action."
    )