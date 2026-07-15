"""AI provider abstraction package (Sprint 1).

Public API:
    AIProvider          - the provider interface every backend must satisfy
    get_provider        - resolve a provider from AI_PROVIDER (factory)
    supported_providers - list of valid AI_PROVIDER values
    text_part/image_part- build provider-neutral message content
"""

from services.ai.factory import get_provider, supported_providers
from services.ai.provider import (
    AIProvider,
    MessageContent,
    image_part,
    normalize_content,
    text_part,
)

__all__ = [
    "AIProvider",
    "MessageContent",
    "get_provider",
    "supported_providers",
    "text_part",
    "image_part",
    "normalize_content",
]
