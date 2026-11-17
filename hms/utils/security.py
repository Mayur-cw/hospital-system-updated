"""
hms/utils/security.py
Security utilities for Hospital Management System:
- Safe redirect validation (S-03)
- Password strength validation (S-06)
- Signed expiring tokens for password reset and email verification (S-12)
"""
from urllib.parse import urlsplit

from flask import redirect, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Common/breached passwords blocked by policy (S-06)
COMMON_PASSWORDS = {
    'password', 'password123', '1234567890', '12345678', 'qwertyuiop',
    'admin12345', 'admin123', 'hospital123', 'hedgewar123', 'welcome123',
    'letmein123', 'doctor1234', 'patient123'
}


def is_safe_url(target: str | None) -> bool:
    """
    Ensure target URL is safe for redirection (S-03).
    Rejects:
    - None or empty targets
    - Protocol-relative URLs ('//evil.com')
    - Backslash URLs ('\\\\evil.com')
    - URLs with external schemes or netlocs ('http://evil.com', 'javascript:...')
    Accepts only same-origin relative paths starting with '/'.
    """
    if not target or not isinstance(target, str):
        return False

    target = target.strip()
    if not target:
        return False

    if target.startswith('//') or target.startswith('\\\\'):
        return False

    try:
        parsed = urlsplit(target)
    except Exception:
        return False

    if parsed.scheme or parsed.netloc:
        return False

    return target.startswith('/')


def safe_redirect(target: str | None, fallback: str = 'main.index', **values):
    """Safely redirect to target or fallback URL (S-03)."""
    if target and is_safe_url(target):
        return redirect(target)
    if fallback.startswith('/'):
        return redirect(fallback)
    return redirect(url_for(fallback, **values))


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Validate password meets industry security policy (S-06):
    - Minimum 10 characters
    - Must not be on common/breached passwords blocklist
    - Never truncated
    """
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty."

    if len(password) < 10:
        return False, "Password must be at least 10 characters long."

    lower_pw = password.lower()
    if lower_pw in COMMON_PASSWORDS:
        return False, "Password is too common or easily guessable. Please choose a stronger passphrase."

    return True, None


def generate_token(payload: dict | int | str, secret_key: str, salt: str = 'hms-token-salt') -> str:
    """Generate cryptographically signed expiring token (S-12)."""
    serializer = URLSafeTimedSerializer(secret_key)
    return serializer.dumps(payload, salt=salt)


def verify_token(token: str, secret_key: str, max_age_seconds: int = 1800, salt: str = 'hms-token-salt'):
    """
    Verify signed token and check expiration (S-12).
    Default max_age: 1800 seconds (30 minutes).
    """
    serializer = URLSafeTimedSerializer(secret_key)
    try:
        data = serializer.loads(token, salt=salt, max_age=max_age_seconds)
        return data
    except (SignatureExpired, BadSignature):
        return None
