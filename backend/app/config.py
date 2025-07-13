"""Configuration settings for Gemini and other AI models"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings


class GeminiConfig(BaseSettings):
    """Gemini API configuration"""
    api_key: str = os.getenv("GOOGLE_API_KEY", "")
    model_name: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("GEMINI_TOP_P", "0.95"))
    top_k: int = int(os.getenv("GEMINI_TOP_K", "64"))
    max_output_tokens: int = int(os.getenv("GEMINI_MAX_TOKENS", "4096"))
    
    class Config:
        env_prefix = "GEMINI_"


class AgentConfig(BaseSettings):
    """General agent configuration"""
    default_agent: str = os.getenv("DEFAULT_AGENT", "smart_search")  # or "gemini_cli"
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # seconds
    max_command_length: int = int(os.getenv("MAX_COMMAND_LENGTH", "1000"))
    command_timeout: int = int(os.getenv("COMMAND_TIMEOUT", "30"))  # seconds
    
    # Security settings
    enable_web_search: bool = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
    allowed_commands: list = [
        "ls", "tree", "find", "cat", "head", "tail", "less", "more",
        "grep", "rg", "awk", "cut", "sort", "uniq", "wc",
        "file", "stat", "du", "pwd"
    ]
    
    class Config:
        env_prefix = "AGENT_"


def get_gemini_config() -> GeminiConfig:
    """Get Gemini configuration"""
    return GeminiConfig()


def get_agent_config() -> AgentConfig:
    """Get agent configuration"""
    return AgentConfig()


# Model configurations for different use cases
MODEL_CONFIGS = {
    "fast": {
        "model": "gemini-2.5-flash",
        "temperature": 0.3,
        "max_output_tokens": 2048
    },
    "balanced": {
        "model": "gemini-2.5-flash",
        "temperature": 0.7,
        "max_output_tokens": 4096
    },
    "creative": {
        "model": "gemini-2.5-flash",
        "temperature": 0.9,
        "max_output_tokens": 8192
    },
    "precise": {
        "model": "gemini-2.5-flash",
        "temperature": 0.1,
        "max_output_tokens": 4096
    }
}


def get_model_config(preset: str = "balanced") -> Dict[str, Any]:
    """Get model configuration by preset"""
    return MODEL_CONFIGS.get(preset, MODEL_CONFIGS["balanced"])