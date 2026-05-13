"""Custom exception hierarchy for the assessment project."""


class AssessmentError(Exception):
    """Base exception for all domain-level errors in this project."""


class DataFetchError(AssessmentError):
    """Raised when external or internal data retrieval fails."""


class DataValidationError(AssessmentError):
    """Raised when raw data is missing, malformed, or semantically invalid."""


class SchemaValidationError(AssessmentError):
    """Raised when structured payload validation fails."""


class LLMServiceError(AssessmentError):
    """Raised when LLM provider calls fail or return invalid responses."""


class LLMProviderError(LLMServiceError):
    """Raised when an LLM provider request fails."""


class LLMValidationError(LLMServiceError):
    """Raised when an LLM provider returns malformed structured output."""


class ProviderAuthenticationError(LLMProviderError):
    """Raised when an LLM provider rejects configured credentials."""


class ProviderRateLimitError(LLMProviderError):
    """Raised when an LLM provider reports rate limiting."""


class ToolExecutionError(AssessmentError):
    """Raised when an agent/tool action fails unexpectedly."""


# Compatibility aliases with concise names used in notebooks and agents.
ValidationError = DataValidationError
LLMError = LLMServiceError
ToolError = ToolExecutionError
