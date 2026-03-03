from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from apps.settings.models import EmailConfiguration
from apps.students.serializers import Parent
import logging
logger = logging.getLogger(__name__)

from apps.students.models import ParentInvite, Parent,StudentParent

User = get_user_model()


class AyaanaTokenSerializer(TokenObtainPairSerializer):
    """Extend JWT payload with role so Flutter can route on login"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']     = user.role
        token['username'] = user.username
        token['email']    = user.email
        return token

    def validate(self, attrs):
        
        email = attrs.get('username', '') 
        if '@' in email:
            try:
                user = User.objects.get(email=email)
                attrs['username'] = user.username
            except User.DoesNotExist:
                pass
        return super().validate(attrs)


class AyaanaLoginView(TokenObtainPairView):
    """
    POST /auth/login/
    Body: { "username": "email@example.com", "password": "..." }
    Returns: { access, refresh, role }
    Works for ALL roles: admin, teacher, parent, etc.
    """
    serializer_class = AyaanaTokenSerializer


class MeView(APIView):
    """
    GET /auth/me/
    Returns the current user's profile + role-specific data.
    Flutter uses this after login to know what to show.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id':         user.id,
            'username':   user.username,
            'email':      user.email,
            'role':       user.role,
            'first_name': user.first_name,
            'last_name':  user.last_name,
        }

        if user.role == 'parent':
            try:
                parent = user.parent_profile
                wards  = parent.wards.values(
                    'id',
                    'admission_number',
                    'first_name',
                    'last_name',
                    'photo_url',
                )
                data['parent'] = {
                    'id':           parent.id,
                    'full_name':    parent.full_name,
                    'phone_number': parent.phone_number,
                    'relationship': parent.relationship,
                    'wards':        list(wards),
                }
            except Parent.DoesNotExist:
                data['parent'] = None

        return Response(data)


class CheckInviteView(APIView):
    """
    GET /auth/invite/check/?code=XXXXXXXX
    Flutter calls this before showing the registration form
    so it can display the parent's name and linked students.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code', '').strip().upper()
        if not code:
            return Response({'error': 'Code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invite = ParentInvite.objects.select_related('parent').get(code=code)
        except ParentInvite.DoesNotExist:
            return Response({'error': 'Invalid invite code.'}, status=status.HTTP_404_NOT_FOUND)

        if not invite.is_valid:
            reason = 'already used' if invite.used else 'expired'
            return Response(
                {'error': f'This invite code has {reason}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parent = invite.parent
        wards  = parent.wards.values('id', 'admission_number', 'first_name', 'last_name')

        return Response({
            'valid':      True,
            'code':       code,
            'parent_name': parent.full_name,
            'expires_at': invite.expires_at,
            'wards':      list(wards),
        })


class RedeemInviteView(APIView):
    """
    POST /auth/invite/redeem/
    Body: {
        "code":     "XXXXXXXX",
        "password": "chosen_password"
    }
    - Creates a User account (role=parent) using the parent's existing email
    - Links it to the Parent record
    - Returns JWT tokens so the parent is immediately logged in
    """
    permission_classes = [AllowAny]

    def post(self, request):
        code     = request.data.get('code', '').strip().upper()
        password = request.data.get('password', '').strip()

        if not code:
            return Response({'error': 'Invite code is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password or len(password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invite = ParentInvite.objects.select_related('parent').get(code=code)
        except ParentInvite.DoesNotExist:
            return Response({'error': 'Invalid invite code.'}, status=status.HTTP_404_NOT_FOUND)

        if not invite.is_valid:
            reason = 'already used' if invite.used else 'expired'
            return Response(
                {'error': f'This invite code has {reason}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parent = invite.parent

        if parent.has_app_access:
            return Response(
                {'error': 'This parent already has an app account. Please log in instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not parent.email:
            return Response(
                {'error': 'No email address on file for this parent. Contact the school admin.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=parent.email).exists():
            return Response(
                {'error': 'An account with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = parent.email.split('@')[0]
        base, counter = username, 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=parent.email,
            password=password,
            first_name=parent.first_name,
            last_name=parent.last_name,
            role='parent',
        )

        invite.redeem(user)

        refresh = RefreshToken.for_user(user)
        refresh['role']     = user.role
        refresh['username'] = user.username

        return Response({
            'message': f'Welcome, {parent.full_name}! Your account has been created.',
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'role':    user.role,
        }, status=status.HTTP_201_CREATED)


class RegenerateInviteView(APIView):
    """
    POST /auth/invite/regenerate/
    Body: { "parent_id": 5 }
    Admin-only. Creates a new invite (invalidates old ones by expiry).
    """
    permission_classes = [IsAuthenticated]



    def app_invite_email(self, parent: Parent, invite: ParentInvite):
        try:
            config, _ = EmailConfiguration.objects.get_or_create(id=1)

            to_email = parent.email.strip()
            if not to_email:
                return Response({"error": "Recipient email is required."})

            try:
                validate_email(to_email)
            except ValidationError:
                return Response({"error": "Please provide a valid recipient email address."})

            if config.backend == "console":
                connection = get_connection("django.core.mail.backends.console.EmailBackend")
            else:
                connection = get_connection(
                    backend="django.core.mail.backends.smtp.EmailBackend",
                    host=config.host,
                    port=config.port,
                    username=config.host_user,
                    password=config.host_password,
                    use_tls=config.use_tls,
                )

            from django.utils.html import strip_tags

            subject = f"{config.school_name} - App Invitation"

            wards = parent.wards  
            student_rows = ""
            for w in wards:
                class_name = w.class_obj.class_name if w.class_obj else "N/A"
                student_rows += f"<tr><td><strong>{w.full_name}</strong> — {class_name}</td></tr>"

            primary_student = wards.first()
            primary_student_name = primary_student.full_name if primary_student else "your child"
            primary_class = primary_student.class_obj.class_name if primary_student and primary_student.class_obj else "N/A"
            invite_link = f"http://localhost:3000/parent/activate?code={invite.code}"
            html_message = f"""
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Parent Portal Invitation</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'DM Sans',Helvetica,Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f0f4f8;">
    <tr>
      <td align="center" style="padding:40px 16px;">

        <!-- Main container — flat, no shadow, no rounded corners -->
        <table border="0" cellpadding="0" cellspacing="0" width="600" style="max-width:600px;width:100%;background:#ffffff;">

          <!-- ── TOP ACCENT BAR ── -->
          <tr>
            <td style="background:linear-gradient(90deg,#1a56db 0%,#4f9cf9 60%,#1a56db 100%);height:5px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- ── HERO ── -->
          <tr>
            <td style="background:#ffffff;padding:52px 56px 36px;text-align:center;">

              <!-- Emblem — square, no shadow -->
              <table border="0" cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
                <tr>
                  <td align="center" style="width:68px;height:68px;background:#1a56db;">
                    <span style="font-size:30px;line-height:68px;display:block;">🎓</span>
                  </td>
                </tr>
              </table>

              <!-- School label -->
              <p style="margin:0 0 10px;font-size:11px;font-weight:500;letter-spacing:4px;text-transform:uppercase;color:#1a56db;">
                {config.school_name}
              </p>

              <!-- Headline -->
              <h1 style="margin:0 0 14px;font-family:'Playfair Display',Georgia,serif;font-size:34px;font-weight:700;color:#0f172a;line-height:1.2;letter-spacing:-0.5px;">
                You're Invited to<br/>the Parent Portal
              </h1>

              <!-- Sub-headline -->
              <p style="margin:0;font-size:16px;font-weight:300;color:#64748b;line-height:1.6;">
                Complete your registration to stay connected<br/>with your child's education.
              </p>
            </td>
          </tr>

          <!-- ── THIN RULE ── -->
          <tr>
            <td style="padding:0 56px;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr><td style="border-top:1px solid #e2e8f0;font-size:0;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- ── GREETING ── -->
          <tr>
            <td style="padding:36px 56px 0;font-size:16px;font-weight:300;color:#475569;line-height:1.8;">
              <p style="margin:0 0 12px;">Dear <strong style="color:#0f172a;font-weight:500;">{parent.full_name}</strong>,</p>
              <p style="margin:0;">
                We're pleased to invite you to create your account on the
                <strong style="color:#1a56db;font-weight:500;">{config.school_name} Parent Portal</strong>.
                Through the portal you can monitor your child's academic journey, communicate with
                teachers, and stay up to date with school activities — all in one place.
              </p>
            </td>
          </tr>

          <!-- ── STUDENT SECTION ── -->
          <tr>
            <td style="padding:32px 56px 0;">

              <!-- Section label -->
              <p style="margin:0 0 10px;font-size:10px;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;">
                Registered Student(s)
              </p>

              <!-- Student table — flat bordered -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%"
                     style="border:1px solid #e2e8f0;border-collapse:collapse;">

                <!-- Header row -->
                <tr style="background:#f8fafc;">
                  <td style="padding:10px 20px;font-size:11px;font-weight:500;letter-spacing:1px;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;">
                    Student
                  </td>
                  <td style="padding:10px 20px;font-size:11px;font-weight:500;letter-spacing:1px;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;" align="right">
                    Status
                  </td>
                </tr>

                <!-- Dynamic student rows injected by Python -->
                {student_rows}

              </table>
            </td>
          </tr>

          <!-- ── CTA BUTTON ── -->
          <tr>
            <td align="center" style="padding:40px 56px 0;">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <!-- Flat square button, no shadow, no radius -->
                  <td align="center" style="background:#1a56db;">
                    <a href="{invite_link}"
                       style="display:inline-block;padding:16px 52px;font-family:'DM Sans',Helvetica,Arial,sans-serif;font-size:15px;font-weight:500;color:#ffffff;text-decoration:none;letter-spacing:0.4px;white-space:nowrap;">
                      Complete Registration &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">
                Button not working? Copy this link:<br/>
                <a href="{invite_link}" style="color:#1a56db;word-break:break-all;">{invite_link}</a>
              </p>
            </td>
          </tr>

          <!-- ── EXPIRY NOTICE — left-border strip, no box ── -->
          <tr>
            <td style="padding:28px 56px 0;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%"
                     style="border-left:3px solid #f59e0b;background:#fffbeb;">
                <tr>
                  <td style="padding:14px 20px;">
                    <p style="margin:0;font-size:13px;color:#78716c;line-height:1.6;">
                      ⏳&nbsp; This invitation expires on
                      <strong style="color:#b45309;">{invite.expires_at.strftime('%B %d, %Y')}</strong>.
                      Please register before then.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── THIN RULE ── -->
          <tr>
            <td style="padding:36px 56px 0;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr><td style="border-top:1px solid #e2e8f0;font-size:0;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- ── BENEFITS ── -->
          <tr>
            <td style="padding:28px 56px 0;">
              <p style="margin:0 0 20px;font-size:10px;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;">
                What you'll get access to
              </p>

              <!-- Benefit 1 -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
                <tr>
                  <td width="40" valign="top">
                    <div style="width:34px;height:34px;background:#eff6ff;border:1px solid #bfdbfe;text-align:center;line-height:34px;font-size:15px;">📊</div>
                  </td>
                  <td style="padding-left:14px;" valign="middle">
                    <p style="margin:0;font-size:14px;color:#475569;line-height:1.5;">
                      <strong style="color:#0f172a;font-weight:500;">Academic Records</strong><br/>
                      Grades, attendance, and performance reports in real time.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Benefit 2 -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
                <tr>
                  <td width="40" valign="top">
                    <div style="width:34px;height:34px;background:#eff6ff;border:1px solid #bfdbfe;text-align:center;line-height:34px;font-size:15px;">💬</div>
                  </td>
                  <td style="padding-left:14px;" valign="middle">
                    <p style="margin:0;font-size:14px;color:#475569;line-height:1.5;">
                      <strong style="color:#0f172a;font-weight:500;">Direct Messaging</strong><br/>
                      Communicate with teachers and school staff instantly.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Benefit 3 -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td width="40" valign="top">
                    <div style="width:34px;height:34px;background:#eff6ff;border:1px solid #bfdbfe;text-align:center;line-height:34px;font-size:15px;">📅</div>
                  </td>
                  <td style="padding-left:14px;" valign="middle">
                    <p style="margin:0;font-size:14px;color:#475569;line-height:1.5;">
                      <strong style="color:#0f172a;font-weight:500;">School Calendar &amp; Notices</strong><br/>
                      Stay informed about events, announcements, and deadlines.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── SUPPORT ── -->
          <tr>
            <td style="padding:32px 56px 44px;">
              <p style="margin:0;font-size:13px;color:#64748b;line-height:1.7;border-top:1px solid #e2e8f0;padding-top:28px;">
                Need help? Contact our support team at
                <a href="mailto:{config.default_from_email}" style="color:#1a56db;text-decoration:none;">{config.default_from_email}</a>
              </p>
            </td>
          </tr>

          <!-- ── FOOTER ── -->
          <tr>
            <td style="background:#f8fafc;padding:24px 56px;border-top:1px solid #e2e8f0;" align="center">
              <p style="margin:0 0 6px;font-size:12px;font-weight:500;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">
                {config.school_name}
              </p>
              <p style="margin:0;font-size:11px;color:#cbd5e1;line-height:1.6;max-width:440px;">
                This email is confidential and intended solely for the named recipient.
                Your personal data is handled in accordance with our privacy policy and
                applicable data-protection laws (GDPR &amp; applicable local law).
              </p>
            </td>
          </tr>

          <!-- ── BOTTOM ACCENT BAR ── -->
          <tr>
            <td style="background:linear-gradient(90deg,#1a56db 0%,#4f9cf9 60%,#1a56db 100%);height:3px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

        </table>
        <!-- /container -->

      </td>
    </tr>
  </table>

</body>
</html>
            """

            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=config.default_from_email or config.host_user,
                recipient_list=[to_email],
                html_message=html_message,
                connection=connection,
                fail_silently=False,
            )

            return Response({"message": "Invite email sent successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Failed to send invite email.")
            message = str(e) if settings.DEBUG else "Failed to send invite email."
            return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        if request.user.role not in ('admin', 'headmaster'):
            return Response({'error': 'Only admins can generate invite codes.'}, status=status.HTTP_403_FORBIDDEN)

        parent_id = request.data.get('parent_id')
        try:
            parent = Parent.objects.get(pk=parent_id)
        except Parent.DoesNotExist:
            return Response({'error': 'Parent not found.'}, status=status.HTTP_404_NOT_FOUND)

        if parent.has_app_access:
            return Response(
                {'error': 'This parent already has an account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invite = ParentInvite.objects.create(
            parent=parent,
            created_by=request.user,
        )
        self.app_invite_email(parent=parent, invite=invite)
 
        


        return Response({
            'code':       invite.code,
            'expires_at': invite.expires_at,
            'parent':     parent.full_name,
        }, status=status.HTTP_201_CREATED)
    

class RevokeInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('admin', 'headmaster'):
            return Response({'error': 'Only admins can revoke invite codes.'}, status=403)

        parent_id = request.data.get('parent_id')
        try:
            parent = Parent.objects.get(pk=parent_id)
        except Parent.DoesNotExist:
            return Response({'error': 'Parent not found.'}, status=404)

        updated = ParentInvite.objects.filter(
            parent=parent,
            used=False,
        ).update(
            used=True,
            used_at=timezone.now(),
        )

        if updated == 0:
            return Response({'message': 'No active invites found for this parent.'}, status=200)

        return Response({'message': f'{updated} invite(s) revoked successfully.'}, status=200)