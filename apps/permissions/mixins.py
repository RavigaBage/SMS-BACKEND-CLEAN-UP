import logging
import re
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from apps.accounts.models import User
from apps.timetable.models import Timetable  # adjust import path if needed

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Standalone ownership checker
# ─────────────────────────────────────────────────────────────────────────────

def check_teacher_ownership(user, teacher_id=None, class_obj_id=None):
    """
    Raises PermissionDenied if the requesting user is not allowed to
    create/edit the resource described by teacher_id + class_obj_id.

    Admin / Headmaster  → always pass
    Teacher             → must match teacher_id AND be timetable-assigned to class
    Anything else       → denied
    """
    if not (user and user.is_authenticated):
        raise PermissionDenied("Authentication required.")

    if user.role in [User.Role.ADMIN, User.Role.HEADMASTER]:
        return

    if user.role == User.Role.TEACHER:
        try:
            teacher_profile = user.teacher_profile  # adjust related_name if needed
        except Exception:
            raise PermissionDenied("No teacher profile is linked to this account.")

        # Only check if the frontend actually sent a teacher_id
        if teacher_id is not None and int(teacher_id) != teacher_profile.id:
            raise PermissionDenied(
                "You can only create or edit records assigned to yourself as the teacher."
            )

        if class_obj_id is not None:
            assigned = Timetable.objects.filter(
                teacher=teacher_profile,
                class_obj_id=int(class_obj_id),
            ).exists()
            if not assigned:
                raise PermissionDenied(
                    "You are not assigned to this class and cannot manage records for it."
                )
        return

    raise PermissionDenied("You do not have permission to perform this action.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Shared exception handler
# ─────────────────────────────────────────────────────────────────────────────

def _parse_validation_error(e):
    if hasattr(e, "message_dict"):
        return e.message_dict
    if hasattr(e, "messages") and e.messages:
        return e.messages[0]
    return str(e)


def handle_viewset_exception(e, action_label: str):
    """
    Central exception → Response converter.
    Covers PermissionDenied, DRF ValidationError, Django ValidationError,
    IntegrityError, and any unexpected exception.
    """
    if isinstance(e, PermissionDenied):
        logger.warning(f"Permission denied while {action_label}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

    if isinstance(e, DRFValidationError):
        logger.error(f"Validation error while {action_label}: {e.detail}")
        return Response(
            {"error": "Validation Error", "detail": e.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(e, DjangoValidationError):
        detail = _parse_validation_error(e)
        logger.error(f"Validation error while {action_label}: {detail}")
        return Response(
            {"error": f"Validation Error: {detail}", "detail": detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(e, IntegrityError):
        error_str = str(e).lower()
        logger.error(f"Integrity error while {action_label}: {e}")

        if "not null" in error_str or "null value" in error_str:
            match = re.search(r"not null constraint failed: \w+\.(\w+)", error_str)
            field = match.group(1) if match else "a required field"
            return Response(
                {"error": f"Missing required field: '{field}' cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if any(tok in error_str for tok in ["unique", "duplicate", "already exists"]):
            return Response(
                {"error": "A record with these details already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"error": "A database constraint was violated.", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.error(f"Unexpected error while {action_label}: {e}", exc_info=True)
    return Response(
        {"error": f"Server Error: An unexpected error occurred while {action_label}."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. The mixin
# ─────────────────────────────────────────────────────────────────────────────

class SchoolWriteMixin:
    """
    Drop-in mixin for any ModelViewSet in this project.

    What it does
    ------------
    - Enforces teacher ownership on create / update / destroy
    - Injects the correct Teacher from the auth token on create/update
      so teachers never need to send teacher_id (and can't spoof it)
    - Standardised exception handling across all write operations

    Config (optional overrides)
    ---------------------------
    ownership_teacher_field = "teacher"    # serializer source field name
    ownership_class_field   = "class_obj"  # request.data key for class ID
    """

    ownership_teacher_field = "teacher"
    ownership_class_field   = "class_obj"
    serializer_teacher_field = "teacher" 
    requires_teacher         = True 

    # ── ownership helpers ─────────────────────────────────────────────────────

    def _check_ownership_from_request(self, request):
        """
        Ownership check reads from request.data.
        For teachers: teacher_id is stripped in to_internal_value so this
        only catches explicit spoofing attempts from non-teacher roles.
        """
        check_teacher_ownership(
            request.user,
            teacher_id=request.data.get(self.ownership_teacher_field),
            class_obj_id=request.data.get(self.ownership_class_field),
        )

    def _check_ownership_from_instance(self, instance):
        check_teacher_ownership(
            self.request.user,
            teacher_id=getattr(getattr(instance, "teacher", None), "id", None),
            class_obj_id=getattr(getattr(instance, "class_obj", None), "id", None),
        )

    # ── teacher profile resolver ──────────────────────────────────────────────

    def _resolve_teacher_profile(self):
        """
        Returns the Teacher profile linked to the current user.
        Returns None for admins/headmasters (they pass teacher_id in payload).
        Raises PermissionDenied if a teacher role has no linked profile.
        """
        user = self.request.user
        if user.role == User.Role.TEACHER:
            try:
                return user.teacher_profile  # adjust related_name if needed
            except Exception:
                raise PermissionDenied("No teacher profile is linked to this account.")
        return None

    # ── perform_create / perform_update: inject teacher from auth token ───────
    def perform_create(self, serializer):
        if not self.requires_teacher:       # ← skip teacher logic entirely
            serializer.save()
            return

        teacher = self._resolve_teacher_profile()
        field = self.serializer_teacher_field
        if teacher is not None:
            serializer.save(**{field: teacher})
        else:
            if not serializer.validated_data.get(field):
                raise DRFValidationError({field: "This field is required."})
            serializer.save()

    def perform_update(self, serializer):
        if not self.requires_teacher:       # ← skip teacher logic entirely
            serializer.save()
            return

        teacher = self._resolve_teacher_profile()
        field = self.serializer_teacher_field
        if teacher is not None:
            serializer.save(**{field: teacher})
        else:
            if not serializer.validated_data.get(field):
                raise DRFValidationError({field: "This field is required."})
            serializer.save()
    # ── overridden CRUD methods ───────────────────────────────────────────────

    def create(self, request, *args, **kwargs):
        try:
            self._check_ownership_from_request(request)
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return handle_viewset_exception(e, f"creating {self._resource_label()}")

    def update(self, request, *args, **kwargs):
        try:
            self._check_ownership_from_request(request)
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return handle_viewset_exception(e, f"updating {self._resource_label()}")

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self._check_ownership_from_instance(instance)
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return handle_viewset_exception(e, f"deleting {self._resource_label()}")

    # ── utility ──────────────────────────────────────────────────────────────

    def _resource_label(self):
        name = type(self).__name__.replace("ViewSet", "").replace("View", "")
        return re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower()