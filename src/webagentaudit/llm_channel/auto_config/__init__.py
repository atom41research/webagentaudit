"""Auto-configuration: algorithmic discovery of LLM chat elements."""

from .base import BaseAutoConfigurator
from .botpress import BotpressAutoConfigurator
from .chatbase import ChatbaseAutoConfigurator
from .chatbot_com import ChatbotComAutoConfigurator
from .configurator import AlgorithmicAutoConfigurator
from .denser import DenserAutoConfigurator
from .intercom import IntercomAutoConfigurator
from .models import AutoConfigResult
from .tidio import TidioAutoConfigurator
from .voiceflow import VoiceflowAutoConfigurator

__all__ = [
    "AlgorithmicAutoConfigurator",
    "BotpressAutoConfigurator",
    "ChatbaseAutoConfigurator",
    "ChatbotComAutoConfigurator",
    "DenserAutoConfigurator",
    "IntercomAutoConfigurator",
    "TidioAutoConfigurator",
    "VoiceflowAutoConfigurator",
    "AutoConfigResult",
    "BaseAutoConfigurator",
]
