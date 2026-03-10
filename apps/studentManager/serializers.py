from rest_framework import serializers
from .models import StudentProgression
from django.db import transaction

class StudentProgressionSerializer(serializers.ModelSerializer):
    """Full serializer — used for retrieve / create / update."""

    student_name    = serializers.CharField(source='student.__str__', read_only=True)
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


    def validate(self, attrs):
        from_class = attrs.get('from_class', getattr(self.instance, 'from_class', None))
        to_class   = attrs.get('to_class',   getattr(self.instance, 'to_class',   None))
        status     = attrs.get('status',     getattr(self.instance, 'status',     'pending'))

        if to_class and from_class == to_class:
            raise serializers.ValidationError(
                "from_class and to_class must be different."
            )

        if status in ('promoted', 'demoted') and not to_class:
            raise serializers.ValidationError(
                f"A destination class (to_class) is required when status is '{status}'."
            )

        return attrs


    def create(self, validated_data):
        request      = self.context.get('request')
        student      = validated_data['student']
        academic_year = validated_data['academic_year']
        from_class   = validated_data['from_class']

        if StudentProgression.objects.filter(
            student=student,
            academic_year=academic_year,
            from_class=from_class,      
        ).exists():
            raise serializers.ValidationError(
                "A progression record for this student, year, and class already exists."
            )

        if request and request.user.is_authenticated:
            validated_data['updated_by'] = request.user

        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        request = self.context.get('request')

        if instance.status != 'pending':
            raise serializers.ValidationError(
                "Completed progression records cannot be modified."
            )

        if request and request.user.is_authenticated:
            validated_data['updated_by'] = request.user

        try:
            with transaction.atomic():
                updated_instance = super().update(instance, validated_data)

                if updated_instance.status in ('promoted', 'demoted', 'graduated', 'withheld'):
                    updated_instance.apply_to_enrollment()  
        except ValueError as e:
            raise serializers.ValidationError({"enrollment": str(e)})

        return updated_instance

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