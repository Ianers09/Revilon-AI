from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminUserDetailView,
    AdminUserListView,
    AdminSetPasswordView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    ProfilePictureView,
    ProfilePictureContentView,
    ProfileView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationView,
    VerifyEmailView,
)


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_scope = "token_refresh"


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "verify-email/",
        VerifyEmailView.as_view(),
        name="verify-email",
    ),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path(
        "profile/picture/",
        ProfilePictureView.as_view(),
        name="profile-picture",
    ),
    path(
        "profile/picture/<int:user_id>/",
        ProfilePictureContentView.as_view(),
        name="profile-picture-content",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "admin/users/",
        AdminUserListView.as_view(),
        name="admin-user-list",
    ),
    path(
        "admin/users/<int:user_id>/",
        AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "admin/users/<int:user_id>/password/",
        AdminSetPasswordView.as_view(),
        name="admin-user-password",
    ),
]
