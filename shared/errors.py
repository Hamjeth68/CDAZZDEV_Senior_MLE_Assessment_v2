"""Custom exception hierarchy for the assessment project."""


class AssessmentError(Exception):
    """Base exception for all domain-level errors in this project."""


class DataFetchError(AssessmentError):
    """Raised when external or internal data retrieval fails."""


class SchemaValidationError(AssessmentError):
    """Raised when structured payload validation fails."""


class LLMServiceError(AssessmentError):
    """Raised when LLM provider calls fail or return invalid responses."""


class ToolExecutionError(AssessmentError):
    """Raised when an agent/tool action fails unexpectedly."""


# LLM Provider-specific exceptions
class LLMProviderError(AssessmentError):
    """Base exception for LLM provider errors."""


class LLMValidationError(LLMProviderError):
    """Raised when LLM output validation fails (e.g., invalid JSON)."""


class ProviderAuthenticationError(LLMProviderError):
    """Raised when provider authentication fails (missing/invalid API key)."""


class ProviderRateLimitError(LLMProviderError):
    """Raised when provider rate limit is exceeded."""
