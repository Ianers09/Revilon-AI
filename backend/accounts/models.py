import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def profile_picture_upload_path(instance, filename):
    extension = Path(filename).suffix.lower() or ".jpg"
    return f"profile_pictures/user_{instance.user_id}/{uuid.uuid4().hex}{extension}"


def validate_profile_picture_size(image):
    maximum_size = 5 * 1024 * 1024
    if image.size > maximum_size:
        raise ValidationError("Profile pictures must be 5 MB or smaller.")


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        validators=[validate_profile_picture_size],
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"Profile for {self.user.username}"


class EmailVerificationCode(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Email verification for {self.user.username}"
