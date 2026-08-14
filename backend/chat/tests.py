from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Conversation, Message
from .services import (
    _conversation_messages,
    _explicitly_asks_middle_name,
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
        self.assertIn(
            "Bachelor of Science in Information Technology student at Cebu Institute",
            system_message["content"],
        )
        self.assertIn("of Technology – University (CIT-U)", system_message["content"])
        self.assertIn("Never identify the\ninstitution only as CIT", system_message["content"])
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

        self.assertIn('middle name is "Manugas"', system_content)
        self.assertIn('first name is "Ian Oliver"', system_content)
        self.assertIn('last name is "Mingoy"', system_content)
        self.assertIn("Always refer to him as Ian Oliver M. Mingoy", system_content)
        self.assertIn('answer exactly: "His middle name is Manugas."', system_content)
        self.assertIn('Do not use the phrase "stands for"', system_content)
        self.assertIn('bare reference to "Ian"', system_content)

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

    def test_middle_name_requires_an_explicit_question(self):
        self.assertFalse(_explicitly_asks_middle_name("Tell me everything about Ian Mingoy"))
        self.assertFalse(_explicitly_asks_middle_name("Give me his official profile"))
        self.assertTrue(_explicitly_asks_middle_name("What is his middle name?"))
        self.assertTrue(_explicitly_asks_middle_name("What is his mn?"))
        self.assertTrue(_explicitly_asks_middle_name("mn?"))
        self.assertTrue(_explicitly_asks_middle_name("middlename"))
        self.assertTrue(_explicitly_asks_middle_name("ians middlename"))
        self.assertTrue(_explicitly_asks_middle_name("Ian's middle name"))
        self.assertTrue(_explicitly_asks_middle_name("What does M. stand for?"))

    def test_fresh_ian_middle_name_question_identifies_the_creator(self):
        user = get_user_model().objects.create_user(
            username="fresh-middle-name-test",
            email="fresh-middle-name@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="ians middlename",
        )

        self.assertEqual(
            generate_ai_response(conversation),
            "If you mean Ian Oliver M. Mingoy, the creator of Revilon AI, "
            "his middle name is Manugas.",
        )

    def test_middle_name_abbreviation_and_follow_up_are_understood(self):
        user = get_user_model().objects.create_user(
            username="middle-abbreviation-test",
            email="middle-abbreviation@example.com",
            password="test-password",
        )
        conversation = Conversation.objects.create(user=user)
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Ian Oliver M. Mingoy is the founder of Revilon AI.",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="mn?",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="M.",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="What is it?",
        )

        self.assertEqual(generate_ai_response(conversation), "His middle name is Manugas.")

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
            "His middle name is Manugas.",
        )
