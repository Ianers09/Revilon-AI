from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    SendMessageView,
)


urlpatterns = [
    path(
        "conversations/",
        ConversationListView.as_view(),
        name="conversation-list",
    ),
    path(
        "conversations/<int:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "messages/",
        SendMessageView.as_view(),
        name="send-message",
    ),
]