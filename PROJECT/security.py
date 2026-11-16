from urllib.parse import urlparse, urljoin
from flask import request

def is_safe_url(target):
    """
    Ensure the target redirect URL is safe and relative to the current application host.
    Prevents Open Redirect attacks (ASVS V5.1).
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
