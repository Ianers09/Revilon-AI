import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


SYSTEM_INSTRUCTIONS = """
You are Revilon AI, a professional, thoughtful, and reliable AI assistant.

Answer the user's request directly and clearly. Use plain language unless the
user asks for technical detail. Be concise for simple questions and thorough
when the task needs explanation. Preserve useful context from earlier messages
in the conversation. When you are uncertain, say so instead of inventing facts.
Do not claim to have performed actions you did not perform. Do not mention these
instructions. Identify yourself as Revilon AI if the user asks who you are.
""".strip()


class AIServiceError(Exception):
    """A safe AI error that can be returned to the frontend."""


def generate_conversation_title(first_message):
    cleaned = re.sub(r"\s+", " ", first_message).strip()
    cleaned = cleaned.strip(" \t\r\n.,!?;:-")

    if not cleaned:
        return "New conversation"

    words = cleaned.split()
    title = " ".join(words[:8])

    if len(words) > 8:
        title = f"{title}…"

    return title[:60].strip() or "New conversation"


def _conversation_messages(conversation):
    newest_messages = list(
        conversation.messages.order_by("-created_at")[:30]
    )
    newest_messages.reverse()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTIONS,
        }
    ]

    messages.extend(
        {
            "role": message.role,
            "content": message.content,
        }
        for message in newest_messages
    )

    return messages


def generate_ai_response(conversation):
    base_url = settings.OLLAMA_BASE_URL.strip().rstrip("/")
    model = settings.OLLAMA_MODEL.strip() or "llama3.2:3b"

    if not base_url:
        raise AIServiceError(
            "Ollama is not configured. Add OLLAMA_BASE_URL to backend/.env "
            "and restart Django."
        )

    request_body = json.dumps(
        {
            "model": model,
            "messages": _conversation_messages(conversation),
            "stream": False,
            "options": {
                "temperature": 0.7,
            },
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    api_key = settings.OLLAMA_API_KEY.strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(
        f"{base_url}/api/chat",
        data=request_body,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        if error.code in (401, 403):
            raise AIServiceError(
                "Ollama rejected the API key. Check OLLAMA_API_KEY in the "
                "deployment settings."
            ) from error

        if error.code == 404:
            raise AIServiceError(
                f"The Ollama model '{model}' is not available at the "
                "configured Ollama host."
            ) from error

        raise AIServiceError(
            "Ollama could not generate a response. Please try again."
        ) from error
    except (URLError, ConnectionError, socket.timeout, TimeoutError) as error:
        raise AIServiceError(
            "Revilon AI could not connect to Ollama. Make sure Ollama is "
            "installed and running, then try again."
        ) from error

    try:
        payload = json.loads(response_body)
        answer = payload["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise AIServiceError(
            "Ollama returned an invalid response. Please try again."
        ) from error

    if not answer:
        raise AIServiceError(
            "Ollama returned an empty response. Please try the message again."
        )

    return answer
