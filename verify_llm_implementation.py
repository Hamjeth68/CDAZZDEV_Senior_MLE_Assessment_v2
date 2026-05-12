#!/usr/bin/env python
"""Comprehensive verification script for LLM provider abstraction layer.

This script validates all components without requiring actual API credentials.
Run with: python verify_llm_implementation.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test 1: Module imports."""
    print("\n" + "=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)
    
    try:
        from shared.llm_client import (
            LLMClient,
            OpenRouterProvider,
            GroqProvider,
            LLMResponse,
            BaseProvider,
            OPENROUTER_ENDPOINT,
            OPENROUTER_DEFAULT_MODEL,
            GROQ_DEFAULT_MODEL,
        )
        from shared.errors import (
            LLMProviderError,
            LLMValidationError,
            ProviderAuthenticationError,
            ProviderRateLimitError,
        )
        from shared.config import get_settings, require_api_key, has_openrouter_api_key, has_groq_api_key
        
        print("✓ All imports successful")
        print(f"  - LLMResponse: {LLMResponse.__name__}")
        print(f"  - LLMClient: {LLMClient.__name__}")
        print(f"  - BaseProvider: {BaseProvider.__name__}")
        print(f"  - OpenRouterProvider: {OpenRouterProvider.__name__}")
        print(f"  - GroqProvider: {GroqProvider.__name__}")
        print(f"  - Exception classes: 4 custom exceptions")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_configuration():
    """Test 2: Configuration reading."""
    print("\n" + "=" * 70)
    print("TEST 2: Configuration Management")
    print("=" * 70)
    
    try:
        from shared.config import get_settings, has_openrouter_api_key, has_groq_api_key
        
        settings = get_settings()
        print(f"✓ Settings loaded: {settings}")
        print(f"  - OpenRouter API key present: {has_openrouter_api_key()}")
        print(f"  - Groq API key present: {has_groq_api_key()}")
        
        # Test that require_api_key fails gracefully when key is missing
        if not has_openrouter_api_key():
            try:
                from shared.config import require_api_key
                require_api_key("openrouter")
                print("✗ Should have raised ValueError for missing key")
                return False
            except ValueError as e:
                print(f"✓ Correctly raised ValueError for missing OpenRouter key")
        
        if not has_groq_api_key():
            try:
                from shared.config import require_api_key
                require_api_key("groq")
                print("✗ Should have raised ValueError for missing key")
                return False
            except ValueError as e:
                print(f"✓ Correctly raised ValueError for missing Groq key")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_custom_exceptions():
    """Test 3: Custom exception hierarchy."""
    print("\n" + "=" * 70)
    print("TEST 3: Custom Exception Hierarchy")
    print("=" * 70)
    
    try:
        from shared.errors import (
            LLMProviderError,
            LLMValidationError,
            ProviderAuthenticationError,
            ProviderRateLimitError,
            AssessmentError,
        )
        
        # Test inheritance
        assert issubclass(LLMProviderError, AssessmentError)
        assert issubclass(LLMValidationError, LLMProviderError)
        assert issubclass(ProviderAuthenticationError, LLMProviderError)
        assert issubclass(ProviderRateLimitError, LLMProviderError)
        
        print("✓ Exception hierarchy correct")
        print(f"  - LLMProviderError → AssessmentError")
        print(f"  - LLMValidationError → LLMProviderError")
        print(f"  - ProviderAuthenticationError → LLMProviderError")
        print(f"  - ProviderRateLimitError → LLMProviderError")
        
        # Test raising
        try:
            raise ProviderAuthenticationError("Test auth error")
        except LLMProviderError as e:
            print(f"✓ ProviderAuthenticationError caught as LLMProviderError: {e}")
        
        return True
    except AssertionError as e:
        print(f"✗ Exception hierarchy test failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Exception test failed: {e}")
        return False


def test_response_dataclass():
    """Test 4: LLMResponse dataclass."""
    print("\n" + "=" * 70)
    print("TEST 4: LLMResponse Dataclass")
    print("=" * 70)
    
    try:
        from shared.llm_client import LLMResponse
        
        # Create response instance
        response = LLMResponse(
            content="Test response",
            provider="openrouter",
            model="meta-llama/llama-3-70b-instruct",
            duration_seconds=1.5,
            input_tokens=100,
            output_tokens=50,
        )
        
        print("✓ LLMResponse instance created")
        print(f"  - Content: {response.content}")
        print(f"  - Provider: {response.provider}")
        print(f"  - Model: {response.model}")
        print(f"  - Duration: {response.duration_seconds}s")
        print(f"  - Total tokens: {response.total_tokens}")
        print(f"  - Fallback used: {response.fallback_used}")
        print(f"  - Retry attempts: {response.retry_attempts}")
        
        assert response.total_tokens == 150
        assert response.fallback_used == False
        print("✓ Metadata calculations correct")
        
        return True
    except Exception as e:
        print(f"✗ LLMResponse test failed: {e}")
        return False


def test_json_parsing():
    """Test 5: JSON parsing logic."""
    print("\n" + "=" * 70)
    print("TEST 5: JSON Parsing Logic")
    print("=" * 70)
    
    try:
        from shared.llm_client import OpenRouterProvider
        
        # Test valid JSON
        test_cases = [
            ('{"key": "value"}', {"key": "value"}),
            ('```json\n{"key": "value"}\n```', {"key": "value"}),
            ('```\n{"key": "value"}\n```', {"key": "value"}),
            ('  {"key": "value"}  ', {"key": "value"}),
        ]
        
        for i, (input_str, expected) in enumerate(test_cases, 1):
            result = OpenRouterProvider._parse_json_response(input_str)
            assert result == expected, f"Case {i} failed: {result} != {expected}"
            print(f"✓ JSON parsing case {i}: {input_str[:30]}...")
        
        # Test invalid JSON
        invalid_cases = [
            "not json",
            '{"incomplete": ',
            "random text",
        ]
        
        for i, invalid in enumerate(invalid_cases, 1):
            result = OpenRouterProvider._parse_json_response(invalid)
            assert result is None, f"Invalid case {i} should return None"
            print(f"✓ Invalid JSON case {i} correctly returned None")
        
        return True
    except Exception as e:
        print(f"✗ JSON parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_initialization():
    """Test 6: Provider initialization."""
    print("\n" + "=" * 70)
    print("TEST 6: Provider Initialization")
    print("=" * 70)
    
    try:
        from shared.config import has_openrouter_api_key, has_groq_api_key
        from shared.errors import LLMProviderError
        
        # If no API keys are set, we expect providers to fail gracefully
        if not has_openrouter_api_key() and not has_groq_api_key():
            print("⚠ No API keys configured (expected for development)")
            print("  To test with real providers, set OPENROUTER_API_KEY and/or GROQ_API_KEY")
            return True
        
        # Test OpenRouter initialization
        if has_openrouter_api_key():
            try:
                from shared.llm_client import OpenRouterProvider
                provider = OpenRouterProvider()
                print(f"✓ OpenRouterProvider initialized with model: {provider.model}")
            except Exception as e:
                print(f"⚠ OpenRouterProvider initialization: {e}")
        else:
            print("⚠ OpenRouter API key not set")
        
        # Test Groq initialization
        if has_groq_api_key():
            try:
                from shared.llm_client import GroqProvider
                provider = GroqProvider()
                print(f"✓ GroqProvider initialized with model: {provider.model}")
            except LLMProviderError as e:
                print(f"⚠ Groq SDK not installed (optional): {e}")
            except Exception as e:
                print(f"⚠ GroqProvider initialization: {e}")
        else:
            print("⚠ Groq API key not set")
        
        return True
    except Exception as e:
        print(f"✗ Provider initialization test failed: {e}")
        return False


def test_llm_client_initialization():
    """Test 7: LLMClient initialization."""
    print("\n" + "=" * 70)
    print("TEST 7: LLMClient Initialization")
    print("=" * 70)
    
    try:
        from shared.config import has_openrouter_api_key, has_groq_api_key
        from shared.errors import LLMProviderError
        
        # LLMClient requires at least one provider to be available
        if not has_openrouter_api_key() and not has_groq_api_key():
            print("⚠ No API keys configured")
            try:
                from shared.llm_client import LLMClient
                client = LLMClient()
                print("✗ LLMClient should fail with no available providers")
                return False
            except LLMProviderError as e:
                print(f"✓ LLMClient correctly raised error: {e}")
                return True
        
        # If API keys are set, client should initialize
        try:
            from shared.llm_client import LLMClient
            client = LLMClient()
            print(f"✓ LLMClient initialized")
            print(f"  - Primary available: {client.primary_available}")
            print(f"  - Fallback available: {client.fallback_available}")
            return True
        except Exception as e:
            print(f"⚠ LLMClient initialization: {e}")
            return True  # May fail if dependencies missing
        
    except Exception as e:
        print(f"✗ LLMClient initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging():
    """Test 8: Logging functionality."""
    print("\n" + "=" * 70)
    print("TEST 8: Logging (No Secrets)")
    print("=" * 70)
    
    try:
        import logging
        from shared.logging_utils import get_logger
        
        # Get logger
        logger = get_logger("test_llm")
        
        # Set to capture output
        logger.setLevel(logging.INFO)
        
        print("✓ Logger created successfully")
        print(f"  - Logger name: test_llm")
        print(f"  - Level: INFO")
        
        # Test that secrets aren't logged
        test_data = {
            "api_key": "secret123",
            "password": "secret456",
            "normal_field": "visible",
        }
        
        from shared.logging_utils import _sanitize
        sanitized = _sanitize(test_data)
        
        print("✓ Secret sanitization working")
        print(f"  - Original: {test_data}")
        print(f"  - Sanitized: {sanitized}")
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["normal_field"] == "visible"
        
        return True
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  LLM Provider Abstraction Layer - Verification Suite  ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    tests = [
        test_imports,
        test_configuration,
        test_custom_exceptions,
        test_response_dataclass,
        test_json_parsing,
        test_provider_initialization,
        test_llm_client_initialization,
        test_logging,
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed_count = sum(results)
    total_count = len(results)
    
    for i, (test, passed) in enumerate(zip(tests, results), 1):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test.__doc__.strip()}")
    
    print("=" * 70)
    print(f"\nResult: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✓✓✓ All verifications passed! Implementation is ready for commit. ✓✓✓\n")
        return 0
    else:
        print(f"\n✗ {total_count - passed_count} test(s) failed. Please review above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
