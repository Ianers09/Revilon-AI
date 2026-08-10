import secrets
import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def _send_with_brevo(user, subject, message):
    if not settings.BREVO_API_KEY or not settings.BREVO_SENDER_EMAIL:
        raise EmailDeliveryError(
            "Brevo email delivery is not configured."
        )

    payload = json.dumps(
        {
            "sender": {
                "name": settings.BREVO_SENDER_NAME,
                "email": settings.BREVO_SENDER_EMAIL,
            },
            "to": [
                {
                    "email": user.email,
                    "name": user.get_full_name().strip() or user.username,
                }
            ],
            "subject": subject,
            "textContent": message,
        }
    ).encode("utf-8")

    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            if response.status != 201:
                raise EmailDeliveryError(
                    "Brevo did not accept the verification email."
                )
    except (HTTPError, URLError, TimeoutError) as error:
        raise EmailDeliveryError(
            "The verification email could not be sent through Brevo."
        ) from error


def _send_with_smtp(user, subject, message):
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
        raise EmailDeliveryError(
            "The verification email could not be sent."
        ) from error
    finally:
        connection.close()

    if sent_count != 1:
        raise EmailDeliveryError(
            "The verification email could not be sent."
        )


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

    try:
        if settings.EMAIL_PROVIDER == "brevo":
            _send_with_brevo(user, subject, message)
        else:
            _send_with_smtp(user, subject, message)
    except EmailDeliveryError:
        verification.delete()
        raise

    return verification
