from datetime import datetime, time
from decimal import Decimal, InvalidOperation

import pytz

HOSPITAL_TZ = pytz.timezone('Asia/Kolkata')

def to_hospital_tz(dt: datetime, tz_name: str = 'Asia/Kolkata') -> datetime:
    """Convert a UTC or naive datetime to the hospital timezone."""
    if dt is None:
        return None
    tz = pytz.timezone(tz_name)
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = pytz.utc.localize(dt)
    return dt.astimezone(tz)

def format_date(value, fmt: str = '%d %b %Y') -> str:
    """Format date / datetime to human-readable date string (e.g. 17 Nov 2026)."""
    if not value:
        return '—'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = to_hospital_tz(value)
    return value.strftime(fmt)

def format_time(value, fmt: str = '%I:%M %p') -> str:
    """Format time / datetime to 12-hour AM/PM string (e.g. 10:30 AM)."""
    if not value:
        return '—'
    if isinstance(value, str):
        try:
            # Try parsing HH:MM
            parts = value.split(':')
            value = time(int(parts[0]), int(parts[1]))
        except (ValueError, TypeError, IndexError):
            return value
    if isinstance(value, datetime):
        value = to_hospital_tz(value)
    return value.strftime(fmt)

def format_datetime(value, fmt: str = '%d %b %Y, %I:%M %p') -> str:
    """Format datetime to full human-readable string."""
    if not value:
        return '—'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = to_hospital_tz(value)
    return value.strftime(fmt)

def format_currency(value) -> str:
    """Format numeric value as Indian Rupee (en-IN: e.g. ₹ 1,500.00)."""
    if value is None:
        return '₹ 0.00'
    try:
        dec_val = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return f"₹ {value}"

    # Formatting with 2 decimal places
    is_neg = dec_val < 0
    dec_val = abs(dec_val)
    cents = f"{dec_val:.2f}".split('.')[1]
    whole = str(int(dec_val))

    # Indian numbering format (2,2,3)
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_whole = ','.join(groups) + ',' + last3
    else:
        formatted_whole = whole

    prefix = '-₹ ' if is_neg else '₹ '
    return f"{prefix}{formatted_whole}.{cents}"

def register_filters(app):
    """Register all filters with Flask Jinja environment."""
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_time'] = format_time
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['currency'] = format_currency
