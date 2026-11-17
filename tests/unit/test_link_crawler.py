# tests/unit/test_link_crawler.py - Template Link & Form Action Crawler (T-08)
import re
from urllib.parse import urlparse

HREF_REGEX = re.compile(r'href=["\']([^"\']+)["\']')
ACTION_REGEX = re.compile(r'action=["\']([^"\']+)["\']')


def extract_internal_urls(html_text: str) -> set[str]:
    """Extract internal navigation paths from HTML href attributes."""
    urls = set()
    for match in HREF_REGEX.findall(html_text):
        parsed = urlparse(match)
        # Filter internal links (exclude external http/https, mailto, tel, javascript, anchors)
        if not parsed.scheme and not match.startswith(("#", "javascript:", "mailto:", "tel:")):
            path = parsed.path
            if path and path.startswith("/"):
                urls.add(path)
    return urls


def test_t08_anonymous_link_crawler(client):
    """T-08: Crawl public landing and auth pages, verifying all referenced links resolve."""
    public_seeds = ["/", "/login", "/signup", "/doctors", "/search", "/healthz"]

    for seed in public_seeds:
        resp = client.get(seed)
        assert resp.status_code in (200, 302), f"Seed URL {seed} returned status {resp.status_code}"
        if resp.status_code == 200:
            urls = extract_internal_urls(resp.data.decode("utf-8"))
            for target in urls:
                # Ignore static asset requests
                if target.startswith("/static/"):
                    continue
                # Skip parameterized URLs that require specific dynamic IDs
                if any(param in target for param in ("<", "{", "/export/", "/download")):
                    continue
                target_resp = client.get(target)
                assert target_resp.status_code != 404, (
                    f"Broken link detected on public page {seed}: target '{target}' returned 404"
                )


def test_t08_patient_link_crawler(client):
    """T-08: Crawl authenticated patient portal pages, verifying navigation links."""
    client.post("/login", data={"email": "p1@test.local", "password": "PatientPass@123"}, follow_redirects=True)
    patient_seeds = ["/dashboard", "/my_appointments", "/my_bills", "/my_records", "/profile"]

    for seed in patient_seeds:
        resp = client.get(seed)
        assert resp.status_code == 200, f"Patient portal seed {seed} returned {resp.status_code}"
        urls = extract_internal_urls(resp.data.decode("utf-8"))
        for target in urls:
            if target.startswith(("/static/", "/logout")) or "/delete" in target:
                continue
            if any(p in target for p in ("<", "{", "/invoice/", "/receipt/", "/cancel")):
                continue
            target_resp = client.get(target)
            assert target_resp.status_code != 404, (
                f"Broken link detected on patient page {seed}: target '{target}' returned 404"
            )


def test_t08_doctor_link_crawler(client):
    """T-08: Crawl doctor portal views, verifying clinical action links."""
    client.post("/login", data={"email": "doc1@test.local", "password": "DoctorPass@123"}, follow_redirects=True)
    doctor_seeds = ["/dashboard", "/my_appointments", "/doctor_admissions", "/profile"]

    for seed in doctor_seeds:
        resp = client.get(seed)
        assert resp.status_code == 200, f"Doctor portal seed {seed} returned {resp.status_code}"
        urls = extract_internal_urls(resp.data.decode("utf-8"))
        for target in urls:
            if target.startswith(("/static/", "/logout")):
                continue
            if any(p in target for p in ("<", "{", "/mark_attended", "/edit_record", "/add_record")):
                continue
            target_resp = client.get(target)
            assert target_resp.status_code != 404, (
                f"Broken link detected on doctor page {seed}: target '{target}' returned 404"
            )


def test_t08_admin_link_crawler(client):
    """T-08: Crawl admin control plane views, verifying dashboard, room, and setting links."""
    client.post("/login", data={"email": "admin@test.local", "password": "AdminPass@123"}, follow_redirects=True)
    admin_seeds = [
        "/admin/dashboard",
        "/admin/doctors",
        "/admin/patients",
        "/admin/appointments",
        "/admin/rooms",
        "/admin/billing",
        "/admin/staff",
        "/admin/settings",
        "/admin/audit-logs",
    ]

    for seed in admin_seeds:
        resp = client.get(seed)
        assert resp.status_code == 200, f"Admin control seed {seed} returned {resp.status_code}"
        urls = extract_internal_urls(resp.data.decode("utf-8"))
        for target in urls:
            if target.startswith(("/static/", "/logout")) or any(act in target for act in ("/delete", "/export")):
                continue
            if any(p in target for p in ("<", "{", "/edit", "/password", "/discharge")):
                continue
            target_resp = client.get(target)
            assert target_resp.status_code != 404, (
                f"Broken link detected on admin page {seed}: target '{target}' returned 404"
            )
