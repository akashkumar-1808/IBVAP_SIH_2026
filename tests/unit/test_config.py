import pytest
from pydantic import SecretStr
from backend.app.config.settings import Settings


def test_default_settings():
    s = Settings()
    assert s.APP_NAME == "IBVAP-Backend"
    assert s.API_V1_STR == "/api/v1"
    assert s.PORT == 8000
    assert s.EVIDENCE_STORAGE_BUCKET == "evidence"


def test_supabase_configured_detection():
    # Empty settings -> not configured
    s_empty = Settings(SUPABASE_URL=None, SUPABASE_SERVICE_ROLE_KEY=None, SUPABASE_ANON_KEY=None)
    assert s_empty.is_supabase_configured is False

    # Placeholder settings -> not configured
    s_placeholder = Settings(
        SUPABASE_URL="https://your-project-ref.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY=SecretStr("your-supabase-service-role-key-placeholder"),
    )
    assert s_placeholder.is_supabase_configured is False

    # Valid settings -> configured
    s_valid = Settings(
        SUPABASE_URL="https://xyzabcdefg.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY=SecretStr("real-secret-key-1234567890"),
    )
    assert s_valid.is_supabase_configured is True
    assert s_valid.get_service_key_value() == "real-secret-key-1234567890"


def test_secret_masking():
    s = Settings(
        SUPABASE_URL="https://xyz.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY=SecretStr("super_confidential_key"),
    )
    repr_str = repr(s)
    # The actual secret string must not appear in repr
    assert "super_confidential_key" not in repr_str
