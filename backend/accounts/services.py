import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

from .models import EmailVerificationCode


CODE_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60


class EmailDeliveryError(Exception):
    pass


class VerificationRateLimitError(Exception):
    def __init__(self, seconds):
        self.seconds = seconds

        super().__init__(
            f"Wait {seconds} seconds before requesting another code."
        )


def generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def send_verification_code(user, enforce_cooldown=False):
    existing = EmailVerificationCode.objects.filter(
        user=user
    ).first()

    if existing and enforce_cooldown:
        available_at = existing.last_sent_at + timedelta(
            seconds=RESEND_COOLDOWN_SECONDS
        )

        remaining = int(
            (available_at - timezone.now()).total_seconds()
        )

        if remaining > 0:
            raise VerificationRateLimitError(remaining)

    code = generate_code()

    verification, _ = (
        EmailVerificationCode.objects.update_or_create(
            user=user,
            defaults={
                "code_hash": make_password(code),
                "expires_at": (
                    timezone.now()
                    + timedelta(minutes=CODE_EXPIRY_MINUTES)
                ),
                "attempt_count": 0,
            },
        )
    )

    subject = f"{code} is your Revilon AI verification code"

    message = (
        f"Hello {user.first_name or user.username},\n\n"
        "Your Revilon AI verification code is:\n\n"
        f"{code}\n\n"
        f"This code expires in {CODE_EXPIRY_MINUTES} minutes. "
        "Do not share it with anyone.\n\n"
        "If you did not create this account, "
        "you can ignore this email.\n\n"
        "Revilon AI"
    )

    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        timeout=20,
    )

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=(
            settings.EMAIL_HOST_USER
            or settings.DEFAULT_FROM_EMAIL
        ),
        to=[user.email],
        connection=connection,
    )

    try:
        sent_count = email.send(fail_silently=False)
    except Exception as error:
        verification.delete()

        raise EmailDeliveryError(
            "The verification email could not be sent."
        ) from error
    finally:
        connection.close()

    if sent_count != 1:
        verification.delete()

        raise EmailDeliveryError(
            "The verification email could not be sent."
        )

    return verification