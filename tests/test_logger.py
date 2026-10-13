"""Unit tests for logger and sensitive credential masking."""

from python_brain.logger import mask_sensitive_text, register_secret_to_mask


def test_mask_explicit_secret():
    """Explicitly registered secrets must be replaced with ***MASKED***."""
    secret_pass = "MySuperSecretPassword123!"
    register_secret_to_mask(secret_pass)

    raw_message = f"Connecting to broker with password: {secret_pass} on server Exness"
    masked = mask_sensitive_text(raw_message)

    assert secret_pass not in masked
    assert "***MASKED***" in masked


def test_mask_regex_sensitive_patterns():
    """Patterns containing keywords like password, token, secret must be automatically masked."""
    test_cases = [
        ("Login failed for password='SecretKey998'", "SecretKey998"),
        ("Using Telegram bot token=123456:ABC-DEF1234ghIkl-zyx57", "123456:ABC-DEF1234ghIkl-zyx57"),
        ("Internal secret: private_trade_secret_key", "private_trade_secret_key"),
    ]

    for raw, secret_sub in test_cases:
        masked = mask_sensitive_text(raw)
        assert secret_sub not in masked
        assert "***MASKED***" in masked
