from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Conversation, Message
from .services import _conversation_messages, generate_ai_response


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

    def test_middle_name_is_known_but_initial_is_default(self):
        user = get_user_model().objects.create_user(
            username="private-identity-test",
            email="private-identity@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)

        system_content = _conversation_messages(conversation)[0]["content"]

        self.assertIn("middle name is Manugas", system_content)
        self.assertIn("Always refer to him as Ian Oliver M. Mingoy", system_content)
        self.assertIn("Only in that case, answer Manugas", system_content)

    def test_creator_question_has_consistent_response(self):
        user = get_user_model().objects.create_user(
            username="creator-response-test",
            email="creator-response@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Who created this AI?",
        )

        self.assertEqual(
            generate_ai_response(conversation),
            "Revilon AI was created by Ian Oliver M. Mingoy.",
        )

    def test_middle_initial_follow_up_has_consistent_response(self):
        user = get_user_model().objects.create_user(
            username="middle-response-test",
            email="middle-response@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Who created this AI?",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Revilon AI was created by Ian Oliver M. Mingoy.",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="What is M.?",
        )

        self.assertEqual(
            generate_ai_response(conversation),
            "The “M.” in Ian Oliver M. Mingoy stands for Manugas.",
        )
