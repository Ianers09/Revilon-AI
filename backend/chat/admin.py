from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content", "created_at"]
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["title", "user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "role", "short_content", "created_at"]
    list_filter = ["role", "created_at"]
    search_fields = [
        "content",
        "conversation__title",
        "conversation__user__username",
    ]
    readonly_fields = ["created_at"]

    @admin.display(description="Content")
    def short_content(self, message):
        if len(message.content) <= 80:
            return message.content

        return f"{message.content[:77]}…"