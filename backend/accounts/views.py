from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User, update_last_login
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import EmailVerificationCode, Profile
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    ProfileUpdateSerializer,
    ProfilePictureSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserSerializer,
)
from .services import (
    EmailDeliveryError,
    VerificationRateLimitError,
    send_verification_code,
)


def create_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def false_value(value):
    return value in {False, "false", "False", "0", 0}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                user = serializer.save()
                send_verification_code(user)
        except EmailDeliveryError:
            return Response(
                {
                    "detail": (
                        "Your account could not be created because the "
                        "verification email could not be sent. Check the "
                        "backend email configuration and try again."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "message": "A verification code was sent to your email.",
                "verification_required": True,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "verify_email"

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            return Response(
                {"detail": "The verification code is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_active:
            return Response(
                {"detail": "This email address is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification = EmailVerificationCode.objects.filter(user=user).first()

        if verification is None:
            return Response(
                {"detail": "Request a new verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.is_expired:
            return Response(
                {
                    "detail": (
                        "This verification code has expired. Request a new code."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.attempt_count >= 5:
            return Response(
                {
                    "detail": (
                        "Too many incorrect attempts. Request a new code."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        verification.attempt_count += 1
        verification.save(update_fields=["attempt_count"])

        if not check_password(code, verification.code_hash):
            remaining = 5 - verification.attempt_count
            return Response(
                {
                    "detail": (
                        f"The verification code is incorrect. "
                        f"{remaining} attempt{'s' if remaining != 1 else ''} remaining."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=["is_active"])
        verification.delete()
        update_last_login(None, user)
        tokens = create_tokens_for_user(user)

        return Response(
            {
                "message": "Your email has been verified.",
                "user": UserSerializer(
                    user,
                    context={"request": request},
                ).data,
                **tokens,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "resend_verification"

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user is None or user.is_active:
            return Response(
                {
                    "message": (
                        "If an unverified account exists, a new code was sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        try:
            send_verification_code(user, enforce_cooldown=True)
        except VerificationRateLimitError as error:
            return Response(
                {
                    "detail": (
                        f"Wait {error.seconds} seconds before requesting "
                        "another code."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except EmailDeliveryError:
            return Response(
                {"detail": "The verification email could not be sent."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"message": "A new verification code was sent."},
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate = User.objects.filter(username__iexact=username).first()

        if (
            candidate is not None
            and candidate.check_password(password)
            and not candidate.is_active
            and EmailVerificationCode.objects.filter(user=candidate).exists()
        ):
            message = "A new verification code was sent to your email."
            try:
                send_verification_code(candidate, enforce_cooldown=True)
            except VerificationRateLimitError:
                message = (
                    "A verification code was recently sent to your email."
                )
            except EmailDeliveryError:
                return Response(
                    {
                        "detail": (
                            "Your password is correct, but the verification "
                            "email could not be sent. Please try again."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            return Response(
                {
                    "detail": message,
                    "code": "email_not_verified",
                    "email": candidate.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user = authenticate(
            request=request,
            username=candidate.username if candidate is not None else username,
            password=password,
        )

        if user is None:
            return Response(
                {"detail": "The username or password is incorrect."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        Profile.objects.get_or_create(user=user)
        update_last_login(None, user)
        tokens = create_tokens_for_user(user)

        return Response(
            {
                "message": "Signed in successfully.",
                "user": UserSerializer(
                    user,
                    context={"request": request},
                ).data,
                **tokens,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        return Response(
            {"message": "Signed out successfully."},
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request):
        Profile.objects.get_or_create(user=request.user)
        return Response(
            UserSerializer(
                request.user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            UserSerializer(
                user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class ProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "profile_picture"

    def post(self, request):
        serializer = ProfilePictureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        picture = serializer.validated_data["profile_picture"]

        profile, _ = Profile.objects.get_or_create(user=request.user)

        profile.profile_picture_data = picture.read()
        profile.profile_picture_content_type = picture.content_type
        profile.save(update_fields=[
            "profile_picture_data", "profile_picture_content_type", "updated_at"
        ])

        return Response(
            UserSerializer(
                request.user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        if profile.profile_picture_data or profile.profile_picture:
            profile.profile_picture.delete(save=False)
            profile.profile_picture = None
            profile.profile_picture_data = None
            profile.profile_picture_content_type = ""
            profile.save()

        return Response(
            UserSerializer(
                request.user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class ProfilePictureContentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        profile = get_object_or_404(Profile, user_id=user_id)
        if not profile.profile_picture_data:
            return Response(status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(
            bytes(profile.profile_picture_data),
            content_type=profile.profile_picture_content_type or "image/jpeg",
        )
        response["Cache-Control"] = "no-store"
        response["Content-Disposition"] = 'inline; filename="profile-image"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "password_change"

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(
            serializer.validated_data["new_password"]
        )
        request.user.save(update_fields=["password"])

        return Response(
            {
                "message": (
                    "Password changed successfully. Please sign in again."
                )
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        search = str(request.query_params.get("search", "")).strip()
        users = User.objects.all().order_by("-date_joined")

        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        thirty_days_ago = timezone.now() - timedelta(days=30)
        data = AdminUserSerializer(
            users,
            many=True,
            context={"request": request},
        ).data

        return Response(
            {
                "stats": {
                    "total_users": User.objects.count(),
                    "active_users": User.objects.filter(is_active=True).count(),
                    "administrators": User.objects.filter(is_staff=True).count(),
                    "new_users": User.objects.filter(
                        date_joined__gte=thirty_days_ago
                    ).count(),
                },
                "count": users.count(),
                "users": data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_user(self, user_id):
        return get_object_or_404(User, id=user_id)

    def get(self, request, user_id):
        user = self.get_user(user_id)
        return Response(
            AdminUserSerializer(
                user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, user_id):
        user = self.get_user(user_id)

        if user.is_superuser and user.id != request.user.id:
            return Response(
                {
                    "detail": (
                        "Superuser accounts cannot be modified from this dashboard."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.id == request.user.id:
            if "is_active" in request.data and false_value(
                request.data.get("is_active")
            ):
                return Response(
                    {"detail": "You cannot disable your own account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "is_staff" in request.data and false_value(
                request.data.get("is_staff")
            ):
                return Response(
                    {
                        "detail": (
                            "You cannot remove your own administrator access."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "is_staff" in request.data and not request.user.is_superuser:
            return Response(
                {"detail": "Only a superuser can change administrator access."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AdminUserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            AdminUserSerializer(
                user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, user_id):
        user = self.get_user(user_id)

        if user.id == request.user.id:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_superuser:
            return Response(
                {
                    "detail": (
                        "Superuser accounts cannot be deleted from this dashboard."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        username = user.username
        user.delete()
        return Response(
            {"message": f'User "{username}" was deleted successfully.'},
            status=status.HTTP_200_OK,
        )
