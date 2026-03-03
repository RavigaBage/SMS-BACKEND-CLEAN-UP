from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_parent_invite_email(invite):
    """
    Send an invite code email to a parent.

    Usage:
        from apps.students.email import send_parent_invite_email
        send_parent_invite_email(invite)

    Returns:
        (success: bool, error: str | None)
    """
    parent = invite.parent

    if not parent.email:
        return False, "No email address on file for this parent."

    wards = parent.wards.values('first_name', 'last_name', 'admission_number')

    context = {
        'school_name':  getattr(settings, 'SCHOOL_NAME', 'Ayaana School'),
        'parent_name':  parent.full_name,
        'invite_code':  invite.code,
        'expires_at':   invite.expires_at.strftime('%d %b %Y at %H:%M'),
        'wards':        list(wards),
        'steps': [
            'Download the Ayaana app on your phone.',
            'On the login screen, tap "Redeem Invite Code".',
            f'Enter the code: {invite.code}',
            'Choose a secure password for your account.',
            'You\'re in! View your child\'s attendance, fees, and academic reports.',
        ],
    }

    html_content = render_to_string('emails/parent_invite.html', context)

    text_content = (
        f"Dear {parent.full_name},\n\n"
        f"You have been invited to access the {context['school_name']} Parent Portal.\n\n"
        f"Your invite code is: {invite.code}\n"
        f"Expires: {context['expires_at']}\n\n"
        f"Steps:\n"
        f"1. Download the Ayaana app\n"
        f"2. Tap 'Redeem Invite Code'\n"
        f"3. Enter the code above\n"
        f"4. Choose a password\n\n"
        f"If you have any issues, contact the school admin.\n\n"
        f"— {context['school_name']}"
    )

    try:
        msg = EmailMultiAlternatives(
            subject=f"[{context['school_name']}] Your Parent Portal Invite Code",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[parent.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        return True, None

    except Exception as e:
        return False, str(e)