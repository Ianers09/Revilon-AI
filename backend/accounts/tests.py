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


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="owner",
            email="owner@example.com",
            password="Owner-Secure-Password-931!",
        )
        self.admin = User.objects.create_user(
            username="administrator",
            email="administrator@example.com",
            password="Admin-Secure-Password-741!",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member-two",
            email="member-two@example.com",
            password="Member-Secure-Password-651!",
        )

    def test_admin_can_update_ordinary_account_without_role_fields(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.member.id}/",
            {"first_name": "Updated", "is_active": False},
            format="json",
        )
        self.member.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.member.first_name, "Updated")
        self.assertFalse(self.member.is_active)

    def test_superuser_can_promote_an_account_safely(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.member.id}/",
            {"is_superuser": True},
            format="json",
        )
        self.member.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.member.is_superuser)
        self.assertTrue(self.member.is_staff)

    def test_account_and_password_update_are_applied_together(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.member.id}/",
            {
                "first_name": "Managed",
                "new_password": "Combined-Secure-Password-842!",
                "confirm_password": "Combined-Secure-Password-842!",
            },
            format="json",
        )
        self.member.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.member.first_name, "Managed")
        self.assertTrue(self.member.check_password("Combined-Secure-Password-842!"))

    def test_invalid_password_rolls_back_other_account_changes(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.member.id}/",
            {
                "first_name": "Should not persist",
                "new_password": "password",
                "confirm_password": "password",
            },
            format="json",
        )
        self.member.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.member.first_name, "")

    def test_last_active_superuser_cannot_be_disabled(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.superuser.id}/",
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_regular_admin_cannot_change_privileged_roles(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/auth/admin/users/{self.member.id}/",
            {"is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
