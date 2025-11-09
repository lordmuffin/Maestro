"""
Model Registry for LLM Provider and Model Tier Management

This module provides centralized configuration for:
- Available LLM providers (local, claude, gemini, openai)
- Model tiers (fast, standard, premium) mapped to specific models
- Provider availability checking
- Privacy sensitivity classification
"""

import os
import requests
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ModelTier(str, Enum):
    """Available model performance tiers"""
    FAST = "fast"
    STANDARD = "standard"
    PREMIUM = "premium"


class Provider(str, Enum):
    """Available LLM providers"""
    LOCAL = "local"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"


class SensitivityLevel(str, Enum):
    """Data sensitivity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Model tier mappings for each provider
MODEL_REGISTRY: Dict[str, Dict[str, str]] = {
    "local": {
        "fast": "llama2",
        "standard": "llama2:7b",
        "premium": "llama2:13b"
    },
    "claude": {
        "fast": "claude-3-haiku-20240307",
        "standard": "claude-3-5-sonnet-20241022",
        "premium": "claude-3-5-opus-20250514"
    },
    "gemini": {
        "fast": "gemini-1.5-flash",
        "standard": "gemini-1.5-pro",
        "premium": "gemini-2.0-flash-exp"
    },
    "openai": {
        "fast": "gpt-3.5-turbo",
        "standard": "gpt-4o",
        "premium": "gpt-4o"
    }
}


# Provider metadata
PROVIDER_INFO: Dict[str, Dict[str, str]] = {
    "local": {
        "name": "Ollama (Local)",
        "endpoint": "http://localhost:11434",
        "privacy": "maximum",
        "requires_key": "false"
    },
    "claude": {
        "name": "Anthropic Claude",
        "api_key_env": "ANTHROPIC_API_KEY",
        "privacy": "cloud",
        "requires_key": "true"
    },
    "gemini": {
        "name": "Google Gemini",
        "api_key_env": "GOOGLE_API_KEY",
        "privacy": "cloud",
        "requires_key": "true"
    },
    "openai": {
        "name": "OpenAI",
        "api_key_env": "OPENAI_API_KEY",
        "privacy": "cloud",
        "requires_key": "true"
    }
}


def get_model_for_tier(provider: str, tier: str) -> str:
    """
    Get the specific model for a provider and tier.

    Args:
        provider: Provider name (local, claude, gemini, openai)
        tier: Model tier (fast, standard, premium)

    Returns:
        Model identifier string

    Raises:
        ValueError: If provider or tier is invalid
    """
    provider = provider.lower()
    tier = tier.lower()

    if provider not in MODEL_REGISTRY:
        valid_providers = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(
            f"Invalid provider '{provider}'. Valid providers: {valid_providers}"
        )

    if tier not in MODEL_REGISTRY[provider]:
        valid_tiers = ", ".join(MODEL_REGISTRY[provider].keys())
        raise ValueError(
            f"Invalid tier '{tier}' for provider '{provider}'. Valid tiers: {valid_tiers}"
        )

    return MODEL_REGISTRY[provider][tier]


def check_provider_available(provider: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a provider is available (API key set or service reachable).

    Args:
        provider: Provider name to check

    Returns:
        Tuple of (is_available, error_message)
    """
    provider = provider.lower()

    if provider not in PROVIDER_INFO:
        return False, f"Unknown provider '{provider}'"

    info = PROVIDER_INFO[provider]

    # Check local provider (Ollama)
    if provider == "local":
        try:
            response = requests.get(
                f"{info['endpoint']}/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Ollama service returned status {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Ollama service not reachable at {info['endpoint']}: {str(e)}"

    # Check cloud providers (API key required)
    api_key_env = info.get("api_key_env")
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            return False, f"Provider '{provider}' unavailable: {api_key_env} not set"
        return True, None

    return False, f"Provider '{provider}' configuration incomplete"


def get_available_providers() -> List[str]:
    """
    Get list of currently available providers.

    Returns:
        List of provider names that are available
    """
    available = []
    for provider in PROVIDER_INFO.keys():
        is_available, _ = check_provider_available(provider)
        if is_available:
            available.append(provider)
    return available


def check_privacy_warning(provider: str, sensitivity: str) -> Tuple[bool, Optional[str]]:
    """
    Check if using a provider with given sensitivity level should generate a warning.

    Args:
        provider: Provider name
        sensitivity: Sensitivity level (low, medium, high)

    Returns:
        Tuple of (should_warn, warning_message)
    """
    provider = provider.lower()
    sensitivity = sensitivity.lower()

    if provider not in PROVIDER_INFO:
        return False, None

    info = PROVIDER_INFO[provider]

    # Cloud providers with high sensitivity should warn
    if info["privacy"] == "cloud" and sensitivity == "high":
        return True, (
            f"⚠️  Privacy Warning: Using cloud provider '{info['name']}' with "
            f"high-sensitivity data. Consider using 'local' provider for maximum privacy."
        )

    # Cloud providers with medium sensitivity - mild warning
    if info["privacy"] == "cloud" and sensitivity == "medium":
        return True, (
            f"ℹ️  Privacy Note: Using cloud provider '{info['name']}' with "
            f"medium-sensitivity data. Data will be processed externally."
        )

    return False, None


def get_default_tier() -> str:
    """Get the default model tier."""
    return ModelTier.STANDARD.value


def get_provider_info(provider: str) -> Dict[str, str]:
    """
    Get metadata about a provider.

    Args:
        provider: Provider name

    Returns:
        Dictionary of provider information

    Raises:
        ValueError: If provider is invalid
    """
    provider = provider.lower()
    if provider not in PROVIDER_INFO:
        valid_providers = ", ".join(PROVIDER_INFO.keys())
        raise ValueError(
            f"Invalid provider '{provider}'. Valid providers: {valid_providers}"
        )
    return PROVIDER_INFO[provider]


def list_all_models() -> Dict[str, Dict[str, str]]:
    """
    Get all available models across all providers.

    Returns:
        Complete model registry
    """
    return MODEL_REGISTRY.copy()
