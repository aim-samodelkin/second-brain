"""
LLM Infrastructure for Second Brain
Provides unified interface for multiple LLM providers
"""

from .manager import LLMManager
from .base import LLMProvider

__all__ = ['LLMManager', 'LLMProvider']
