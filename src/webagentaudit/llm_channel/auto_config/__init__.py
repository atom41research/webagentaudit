"""Auto-configuration: algorithmic discovery of LLM chat elements."""

from .base import BaseAutoConfigurator
from .configurator import AlgorithmicAutoConfigurator
from .denser import DenserAutoConfigurator
from .intercom import IntercomAutoConfigurator
from .chatbot_com import ChatbotComAutoConfigurator
from .tidio import TidioAutoConfigurator
from .models import AutoConfigResult

__all__ = [
    "AlgorithmicAutoConfigurator",
    "DenserAutoConfigurator",
    "IntercomAutoConfigurator",
    "ChatbotComAutoConfigurator",
    "TidioAutoConfigurator",
    "AutoConfigResult",
    "BaseAutoConfigurator",
]
