import pytest
import os
from security import is_safe_url
from config import Config
from app import create_app

def test_t_config_001_refuses_production_boot_without_secret():
    """T-CONFIG-001: Application refuses production boot if SECRET_KEY or DATABASE_URL is missing."""
    old_env = os.environ.get('APP_ENV')
    old_secret = os.environ.get('SECRET_KEY')
    old_db = os.environ.get('DATABASE_URL')
    try:
        os.environ['APP_ENV'] = 'production'
        os.environ.pop('SECRET_KEY', None)
        os.environ['DATABASE_URL'] = 'mysql://user:pass@127.0.0.1/hms'
        
        with pytest.raises(RuntimeError) as exc_info:
            create_app(Config)
            
        assert "SECRET_KEY" in str(exc_info.value)
    finally:
        if old_env: os.environ['APP_ENV'] = old_env
        else: os.environ.pop('APP_ENV', None)
        if old_secret: os.environ['SECRET_KEY'] = old_secret
        if old_db: os.environ['DATABASE_URL'] = old_db

def test_t_redirect_001_rejects_external_urls(app):
    """T-REDIRECT-001: is_safe_url strictly rejects off-site external redirects."""
    with app.test_request_context('http://127.0.0.1:5001/login'):
        # Safe relative URLs
        assert is_safe_url('/dashboard') is True
        assert is_safe_url('/admin/appointments?date=2026-11-17') is True
        assert is_safe_url('http://127.0.0.1:5001/patient') is True

        # Unsafe external domains
        assert is_safe_url('http://evil.com/phish') is False
        assert is_safe_url('https://google.com') is False
        assert is_safe_url('//attacker.org/steal') is False
        assert is_safe_url('javascript:alert(1)') is False
        assert is_safe_url('') is False
        assert is_safe_url(None) is False

def test_t_csrf_001_blocks_state_mutation_without_token(client):
    """T-CSRF-001: State-mutating POST request fails with 400 Bad Request when CSRF token is omitted."""
    # Attempting to POST /login without CSRF token
    response = client.post('/login', data={'email': 'admin@test.local', 'password': 'Pass'})
    assert response.status_code == 400
    assert b"CSRF" in response.data or b"Bad Request" in response.data
