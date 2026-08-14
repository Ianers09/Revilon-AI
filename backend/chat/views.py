from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    SendMessageSerializer,
    RenameConversationSerializer,
)
from .services import (
    AIServiceError,
    generate_ai_response,
    generate_conversation_title,
)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_conversation(self, request, conversation_id):
        return get_object_or_404(
            Conversation.objects.prefetch_related("messages"),
            id=conversation_id,
            user=request.user,
        )

    def get(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        return Response(ConversationDetailSerializer(conversation).data)

    def delete(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        serializer = RenameConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation.title = serializer.validated_data["title"]
        conversation.save(update_fields=["title", "updated_at"])
        return Response(ConversationListSerializer(conversation).data)


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_message"

    def post(self, request):
        input_serializer = SendMessageSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        content = input_serializer.validated_data["content"]
        conversation_id = input_serializer.validated_data.get(
            "conversation_id"
        )

        with transaction.atomic():
            if conversation_id is None:
                conversation = Conversation.objects.create(
                    user=request.user,
                    title=generate_conversation_title(content),
                )
            else:
                conversation = get_object_or_404(
                    Conversation,
                    id=conversation_id,
                    user=request.user,
                )

            Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=content,
            )
            conversation.save(update_fields=["updated_at"])

        try:
            answer = generate_ai_response(conversation)
        except AIServiceError as error:
            conversation.refresh_from_db()

            return Response(
                {
                    "detail": str(error),
                    "conversation": ConversationDetailSerializer(
                        conversation
                    ).data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=answer,
            )
            conversation.save(update_fields=["updated_at"])

        conversation.refresh_from_db()

        return Response(
            {
                "conversation": ConversationDetailSerializer(
                    conversation
                ).data
            },
            status=status.HTTP_201_CREATED,
        )
