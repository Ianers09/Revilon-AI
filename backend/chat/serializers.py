from rest_framework import serializers

from .models import Conversation, Message

MAX_MESSAGE_LENGTH = 100000


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "messages"]
        read_only_fields = fields


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=MAX_MESSAGE_LENGTH,
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )


class RenameConversationSerializer(serializers.Serializer):
    title = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=255)
