from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="Original-Secure-Password-451!",
            is_active=True,
        )

    @patch("accounts.views.send_password_reset_email")
    def test_request_is_generic_for_existing_and_unknown_email(self, send_email):
        existing = self.client.post(
            "/api/auth/password-reset/",
            {"email": self.user.email},
            format="json",
        )
        unknown = self.client.post(
            "/api/auth/password-reset/",
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(existing.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(existing.data, unknown.data)
        send_email.assert_called_once_with(self.user)

    def test_valid_link_changes_password_and_is_single_use(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        payload = {
            "uid": uid,
            "token": token,
            "new_password": "New-Secure-Password-752!",
            "confirm_password": "New-Secure-Password-752!",
        }

        first = self.client.post(
            "/api/auth/password-reset/confirm/", payload, format="json"
        )
        second = self.client.post(
            "/api/auth/password-reset/confirm/", payload, format="json"
        )
        self.user.refresh_from_db()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertTrue(self.user.check_password("New-Secure-Password-752!"))

    def test_invalid_link_does_not_change_password(self):
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": "invalid",
                "token": "invalid-token",
                "new_password": "New-Secure-Password-752!",
                "confirm_password": "New-Secure-Password-752!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class AdminSetPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin",
            password="Admin-Secure-Password-741!",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member",
            password="Original-Secure-Password-451!",
        )

    def test_admin_can_set_another_users_password(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/auth/admin/users/{self.member.id}/password/",
            {
                "new_password": "Managed-Secure-Password-852!",
                "confirm_password": "Managed-Secure-Password-852!",
            },
            format="json",
        )
        self.member.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.member.check_password("Managed-Secure-Password-852!"))

    def test_admin_cannot_set_own_password_without_current_password(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/auth/admin/users/{self.admin.id}/password/",
            {
                "new_password": "Managed-Secure-Password-852!",
                "confirm_password": "Managed-Secure-Password-852!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_non_admin_is_denied(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(
            f"/api/auth/admin/users/{self.admin.id}/password/",
            {
                "new_password": "Managed-Secure-Password-852!",
                "confirm_password": "Managed-Secure-Password-852!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
