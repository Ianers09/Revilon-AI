from django.contrib.auth import get_user_model
from django.test import TestCase

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
