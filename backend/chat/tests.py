from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Conversation
from .services import _conversation_messages


class RevilonIdentityTests(TestCase):
    def test_creator_identity_is_in_system_instructions(self):
        user = get_user_model().objects.create_user(
            username="identity-test",
            email="identity@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)

        system_message = _conversation_messages(conversation)[0]

        self.assertEqual(system_message["role"], "system")
        self.assertIn("Ian Oliver M. Mingoy", system_message["content"])
        self.assertIn("created", system_message["content"])
        self.assertIn(
            "Bachelor of Science in Information Technology student at CIT",
            system_message["content"],
        )
        self.assertIn("full-stack developer", system_message["content"])
        self.assertIn("Do not\ninvent, assume, or embellish", system_message["content"])

    @override_settings(CREATOR_MIDDLE_NAME="PrivateMiddleName")
    def test_middle_name_is_added_only_from_private_setting(self):
        user = get_user_model().objects.create_user(
            username="private-identity-test",
            email="private-identity@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)

        system_content = _conversation_messages(conversation)[0]["content"]

        self.assertIn("middle name is PrivateMiddleName", system_content)
        self.assertIn("never volunteer", system_content)
