from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Conversation, Message
from .services import (
    _conversation_messages,
    generate_ai_response,
    remove_emojis,
)


class RevilonIdentityTests(TestCase):
    def test_emojis_are_removed_from_ai_output(self):
        self.assertEqual(
            remove_emojis("Hello 👋 Build complete ✅"),
            "Hello  Build complete",
        )

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
        self.assertIn("Founder and Full-Stack Developer, Revilon AI", system_message["content"])
        self.assertIn("Bachelor of Science in Information Technology Student", system_message["content"])
        self.assertIn("Cebu Institute of Technology – University", system_message["content"])
        self.assertIn("Cebu, Philippines", system_message["content"])
        self.assertIn("React, JavaScript, Python, Django REST Framework", system_message["content"])
        self.assertIn("Do not\ninvent, assume, or embellish", system_message["content"])

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

    def test_bare_ian_question_requests_clarification(self):
        user = get_user_model().objects.create_user(
            username="ambiguous-ian-test",
            email="ambiguous-ian@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Who is Ian?",
        )

        self.assertEqual(
            generate_ai_response(conversation),
            "Which Ian do you mean? Please provide a last name or some context.",
        )

    def test_creator_first_name_includes_both_given_names(self):
        user = get_user_model().objects.create_user(
            username="creator-first-name-test",
            email="creator-first-name@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Revilon AI was created by Ian Oliver M. Mingoy.",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="What is his first name?",
        )

        self.assertEqual(generate_ai_response(conversation), "His first name is Ian Oliver.")

    def test_vague_follow_up_does_not_identify_the_creator(self):
        user = get_user_model().objects.create_user(
            username="vague-ian-test",
            email="vague-ian@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Which Ian do you mean? Please provide a last name or some context.",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="I mean the one and only.",
        )

        self.assertEqual(
            generate_ai_response(conversation),
            "I still need a last name or specific context to identify which Ian you mean.",
        )
