from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile


def get_profile_picture_url(user, request=None):
    profile, _ = Profile.objects.get_or_create(user=user)

    if profile.profile_picture_data:
        picture_url = f"/api/auth/profile/picture/{user.id}/"
    elif profile.profile_picture:
        picture_url = profile.profile_picture.url
    else:
        return None

    if request is not None:
        return request.build_absolute_uri(picture_url)

    return picture_url


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "profile_picture",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "profile_picture",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        ]

    def get_profile_picture(self, user):
        return get_profile_picture_url(
            user,
            self.context.get("request"),
        )


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=True,
        allow_blank=False,
    )
    last_name = serializers.CharField(
        max_length=150,
        required=True,
        allow_blank=False,
    )
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
        ]

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def validate_username(self, value):
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.is_active = False
        user.set_password(password)
        user.save()
        Profile.objects.get_or_create(user=user)
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=False,
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=False,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=False,
    )
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
        ]

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def validate_username(self, value):
        username = value.strip()
        exists = User.objects.filter(
            username__iexact=username,
        ).exclude(pk=self.instance.pk).exists()

        if exists:
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        exists = User.objects.filter(
            email__iexact=email,
        ).exclude(pk=self.instance.pk).exists()

        if exists:
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return email



class ProfilePictureSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(required=True)

    def validate_profile_picture(self, image):
        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }
        content_type = getattr(image, "content_type", "")

        if content_type not in allowed_types:
            raise serializers.ValidationError(
                "Use a JPG, PNG, or WEBP image."
            )

        if image.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Profile pictures must be 5 MB or smaller."
            )

        return image


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        required=True,
        error_messages={
            "invalid": "Enter the six-digit verification code.",
        },
    )

    def validate_email(self, value):
        return value.strip().lower()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.strip().lower()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "Your current password is incorrect."
            )
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def validate(self, attributes):
        if attributes["new_password"] != attributes["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "The password confirmation does not match."}
            )
        if attributes["current_password"] == attributes["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "Choose a password different from your current password."}
            )
        return attributes


class AdminUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "first_name",
            "last_name",
            "username",
            "email",
            "profile_picture",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        ]

    def get_display_name(self, user):
        return user.get_full_name().strip() or user.username

    def get_profile_picture(self, user):
        return get_profile_picture_url(
            user,
            self.context.get("request"),
        )


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=False,
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=False,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=False,
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "is_active",
            "is_staff",
        ]

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def validate_username(self, value):
        username = value.strip()
        exists = User.objects.filter(
            username__iexact=username,
        ).exclude(pk=self.instance.pk).exists()
        if exists:
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        exists = User.objects.filter(
            email__iexact=email,
        ).exclude(pk=self.instance.pk).exists()
        if exists:
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return email
