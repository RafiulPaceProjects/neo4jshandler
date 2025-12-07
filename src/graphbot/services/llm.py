import os
import yaml
import abc
import asyncio
import re
from typing import Any, Optional
from dataclasses import dataclass
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Custom exceptions for better error handling
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMRateLimitError(LLMError):
    """Raised when API rate limit is hit."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after

class LLMAuthenticationError(LLMError):
    """Raised when API authentication fails."""
    pass

class LLMModelNotFoundError(LLMError):
    """Raised when the requested model is not found."""
    pass

class LLMTimeoutError(LLMError):
    """Raised when API request times out or is cancelled."""
    pass

class LLMServerError(LLMError):
    """Raised when API server returns 5xx error."""
    pass

@dataclass
class LLMResponse:
    content: str
    token_usage: Optional[dict[str, int]] = None
    model_name: Optional[str] = None

class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.api_key = os.getenv(config.get('api_key_env_var', ''), '')
        self.main_model = config['models'].get('main')
        self.worker_model = config['models'].get('worker')

    @abc.abstractmethod
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None, is_worker: bool = False) -> LLMResponse:
        """Generate text from the LLM."""
        pass

    @abc.abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens for a given text."""
        pass

class GeminiProvider(LLMProvider):
    """Google Gemini implementation with robust error handling and retry logic."""
    
    # Retry configuration
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0  # seconds
    
    # Retryable error patterns
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    RETRYABLE_ERROR_PATTERNS = [
        "cancelled",
        "timeout",
        "deadline exceeded",
        "resource exhausted",
        "unavailable",
        "internal error",
        "stream",
    ]
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        import google.generativeai as genai
        if not self.api_key:
            raise LLMAuthenticationError(f"API key not found for {config.get('provider')}")
        genai.configure(api_key=self.api_key)
        self.genai = genai

    def _classify_error(self, error: Exception) -> tuple[type, Optional[float]]:
        """
        Classify an error and determine if it's retryable.
        
        Returns:
            Tuple of (exception_class, retry_after_seconds or None)
        """
        error_str = str(error).lower()
        
        # Check for status codes in error message
        for code in self.RETRYABLE_STATUS_CODES:
            if str(code) in str(error):
                if code == 429:
                    retry_after = self._extract_retry_time(str(error))
                    return (LLMRateLimitError, retry_after)
                elif code in {500, 502, 503}:
                    return (LLMServerError, None)
                elif code == 504:
                    return (LLMTimeoutError, None)
        
        # Check for specific error patterns
        if "400" in str(error) and ("api key" in error_str or "api_key" in error_str):
            return (LLMAuthenticationError, None)
        
        if "404" in str(error) or "not found" in error_str:
            return (LLMModelNotFoundError, None)
        
        # Check for retryable patterns
        for pattern in self.RETRYABLE_ERROR_PATTERNS:
            if pattern in error_str:
                return (LLMTimeoutError, None)
        
        # Default to generic LLMError
        return (LLMError, None)
    
    def _extract_retry_time(self, error_str: str) -> Optional[float]:
        """Extract retry time from error message if present."""
        try:
            match = re.search(r'retry[^\d]*(\d+(?:\.\d+)?)\s*s', error_str.lower())
            if match:
                return float(match.group(1))
        except (ValueError, AttributeError):
            pass
        return None
    
    def _is_retryable(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        error_class, _ = self._classify_error(error)
        # Don't retry authentication or model-not-found errors
        return error_class not in (LLMAuthenticationError, LLMModelNotFoundError)

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None, is_worker: bool = False) -> LLMResponse:
        """Generate text with automatic retry for transient errors."""
        model_name = self.worker_model if is_worker else self.main_model
        
        # Construct full prompt
        final_prompt = prompt
        if system_instruction:
            final_prompt = f"{system_instruction}\n\n{prompt}"

        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                model = self.genai.GenerativeModel(model_name)
                response = await model.generate_content_async(final_prompt)
                
                text = ""
                if hasattr(response, 'text'):
                    text = response.text
                else:
                    text = self._extract_text_fallback(response)

                # Usage tracking if available
                usage = {}
                if hasattr(response, 'usage_metadata'):
                    usage = {
                        'prompt_tokens': response.usage_metadata.prompt_token_count,
                        'candidates_tokens': response.usage_metadata.candidates_token_count,
                        'total_tokens': response.usage_metadata.total_token_count
                    }

                return LLMResponse(content=text, token_usage=usage, model_name=model_name)
                
            except Exception as e:
                last_error = e
                error_class, retry_after = self._classify_error(e)
                
                # Log the error
                logger.warning(f"Gemini API error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                
                # Check if we should retry
                if not self._is_retryable(e) or attempt == self.MAX_RETRIES - 1:
                    # Convert to appropriate exception type
                    if error_class == LLMAuthenticationError:
                        raise LLMAuthenticationError(
                            f"Invalid API Key. Please check your GEMINI_API_KEY. Original error: {str(e)[:200]}"
                        ) from e
                    elif error_class == LLMModelNotFoundError:
                        raise LLMModelNotFoundError(
                            f"Model '{model_name}' not found. Please check model name. Original error: {str(e)[:200]}"
                        ) from e
                    elif error_class == LLMRateLimitError:
                        raise LLMRateLimitError(
                            f"Rate limit exceeded after {self.MAX_RETRIES} retries. Original error: {str(e)[:200]}",
                            retry_after=retry_after
                        ) from e
                    elif error_class == LLMTimeoutError:
                        raise LLMTimeoutError(
                            f"Request timed out or was cancelled after {self.MAX_RETRIES} retries. Original error: {str(e)[:200]}"
                        ) from e
                    elif error_class == LLMServerError:
                        raise LLMServerError(
                            f"Server error from Gemini API after {self.MAX_RETRIES} retries. Original error: {str(e)[:200]}"
                        ) from e
                    else:
                        raise LLMError(f"LLM generation failed: {str(e)[:200]}") from e
                
                # Calculate retry delay with exponential backoff
                if retry_after:
                    delay = min(retry_after, self.MAX_RETRY_DELAY)
                else:
                    delay = min(self.BASE_RETRY_DELAY * (2 ** attempt), self.MAX_RETRY_DELAY)
                
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
        
        # Should not reach here, but just in case
        raise LLMError(f"Failed after {self.MAX_RETRIES} attempts: {last_error}")

    async def count_tokens(self, text: str) -> int:
        """Count tokens with error handling."""
        try:
            model = self.genai.GenerativeModel(self.main_model)
            return model.count_tokens(text).total_tokens
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            # Fallback to rough estimate (~4 chars per token)
            return len(text) // 4

    def _extract_text_fallback(self, response) -> str:
        """Extract text from response with multiple fallback methods."""
        # Method 1: Try candidates[0].content.parts
        if hasattr(response, 'candidates') and response.candidates:
            try:
                parts = response.candidates[0].content.parts
                return "".join([p.text for p in parts if hasattr(p, 'text')])
            except (AttributeError, IndexError):
                pass
        
        # Method 2: Try parts directly
        if hasattr(response, 'parts'):
            try:
                return "".join([p.text for p in response.parts if hasattr(p, 'text')])
            except (AttributeError, TypeError):
                pass
        
        # Method 3: Try result attribute
        if hasattr(response, 'result'):
            try:
                if hasattr(response.result, 'parts'):
                    return "".join([p.text for p in response.result.parts if hasattr(p, 'text')])
            except (AttributeError, TypeError):
                pass
        
        logger.warning("Could not extract text from response using any known method")
        return ""

class OpenAIProvider(LLMProvider):
    """OpenAI implementation (Stub)."""
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        # Would initialize openai client here
        
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None, is_worker: bool = False) -> LLMResponse:
        return LLMResponse(content="OpenAI Stub Response: " + prompt[:20] + "...", model_name=self.main_model)

    async def count_tokens(self, text: str) -> int:
        return len(text.split()) # Rough approximation for stub

class AnthropicProvider(LLMProvider):
    """Anthropic implementation (Stub)."""
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None, is_worker: bool = False) -> LLMResponse:
        return LLMResponse(content="Anthropic Stub Response: " + prompt[:20] + "...", model_name=self.main_model)

    async def count_tokens(self, text: str) -> int:
        return len(text.split())

class LLMFactory:
    @classmethod
    def get_provider(cls, config_path: str = "config/providers.yaml") -> LLMProvider:
        # Load config
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            
        active_profile_name = full_config.get('active_profile')
        profile_config = full_config['profiles'].get(active_profile_name)
        
        if not profile_config:
            raise ValueError(f"Active profile '{active_profile_name}' not defined in profiles.")
            
        provider_type = profile_config.get('provider')
        
        if provider_type == 'google':
            return GeminiProvider(profile_config)
        elif provider_type == 'openai':
            return OpenAIProvider(profile_config)
        elif provider_type == 'anthropic':
            return AnthropicProvider(profile_config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
            

