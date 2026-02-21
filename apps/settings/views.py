# apps/settings/views.py

import logging

from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import EmailConfiguration
from .serializers import EmailConfigurationSerializer

logger = logging.getLogger(__name__)


def get_config():
    config, _ = EmailConfiguration.objects.get_or_create(id=1)
    return config


@api_view(["GET", "POST"])
def email_settings(request):
    try:
        config = get_config()

        if request.method == "GET":
            serializer = EmailConfigurationSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = EmailConfigurationSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {
                "error": "Invalid email configuration data.",
                "details": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.exception("Failed to process email settings request.")
        message = str(e) if settings.DEBUG else "Unable to process email settings right now."
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def test_email(request):
    try:
        config = get_config()
        to_email = (request.data.get("to") or "").strip()

        if not to_email:
            return Response(
                {"error": "Recipient email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_email(to_email)
        except ValidationError:
            return Response(
                {"error": "Please provide a valid recipient email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

            subject = f"{config.school_name} - Email Configuration Test"

            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="UTF-8">
            <title>Email Test</title>
            </head>
            <body style="margin:0; padding:0; background-color:#f4f6f9; font-family:Arial, sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
                <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0"
                        style="background:#ffffff; border-radius:12px; padding:40px; box-shadow:0 4px 20px rgba(0,0,0,0.05);">

                    <tr>
                        <td align="center" style="padding-bottom:25px;">
                        <h1 style="margin:0; font-size:22px; color:#1f3889;">
                            {config.school_name}
                        </h1>
                        <p style="margin:6px 0 0; font-size:14px; color:#6b7280;">
                            Email System Test
                        </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="font-size:15px; color:#374151; line-height:1.6;">
                        <p>Hello,</p>

                        <p>
                            This is a confirmation that your email configuration has been
                            successfully connected and is working properly.
                        </p>

                        <p>
                            Your system is now capable of sending:
                        </p>

                        <ul style="padding-left:18px; margin:10px 0;">
                            <li>Student reports and transcripts</li>
                            <li>Parent notifications</li>
                            <li>Fee reminders</li>
                            <li>Academic updates</li>
                        </ul>

                        <p>
                            If you received this message, your SMTP credentials,
                            authentication, and security settings are correctly configured.
                        </p>

                        <p style="margin-top:25px;">
                            You may now proceed with confidence.
                        </p>

                        <p style="margin-top:30px;">
                            Best regards,<br>
                            <strong>{config.school_name} Administration System</strong>
                        </p>
                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="padding-top:30px; font-size:12px; color:#9ca3af;">
                        This is an automated test message. No action is required.
                        </td>
                    </tr>

                    </table>
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


        return Response({"message": "Test email sent successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Failed to send test email.")
        message = str(e) if settings.DEBUG else (
            "Failed to send test email. Please verify email settings and try again."
        )
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
