"""
Phase 4 Verification Suite: Design System & UI/UX Overhaul (U-01 through U-16)

Validates:
1. Contrast ratio verification via tools/check_contrast.py (WCAG 2.2 AA).
2. Zero <style> tags in any Jinja template.
3. Zero inline style= attributes in any Jinja template.
4. Zero inline onclick= handlers in any Jinja template.
5. Zero raw hex color values outside tokens.css in core styles.
6. Component macro library presence and rendering.
7. Role-aware app and public layouts.
8. Self-hosted assets (DM Sans, Syne, Bootstrap, FontAwesome) without external CDN dependencies.
"""

import re
import subprocess
import sys
from pathlib import Path

from flask import render_template_string

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "hms" / "templates"
STATIC_DIR = PROJECT_ROOT / "hms" / "static"


def test_u01_wcag_contrast_script_passes():
    """U-01: Verify all 24 semantic token pairs pass WCAG 2.2 AA contrast ratios."""
    script_path = PROJECT_ROOT / "tools" / "check_contrast.py"
    assert script_path.exists(), "check_contrast.py must exist"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False
    )
    assert result.returncode == 0, f"Contrast check failed:\n{result.stdout}\n{result.stderr}"
    assert "24 passed, 0 failed" in result.stdout


def test_u14_zero_style_tags_in_templates():
    """U-14: Zero <style> or <style ...> blocks across all application templates."""
    style_tag_pattern = re.compile(r"<style[\s>]", re.IGNORECASE)
    violations = []

    for template_file in TEMPLATES_DIR.rglob("*.html"):
        content = template_file.read_text(encoding="utf-8")
        if style_tag_pattern.search(content):
            violations.append(str(template_file.relative_to(PROJECT_ROOT)))

    assert not violations, "Found <style> tags in templates:\n" + "\n".join(violations)


def test_u14_zero_inline_style_attributes_in_templates():
    """U-14: Zero inline style= attributes across all application templates."""
    style_attr_pattern = re.compile(r"""\bstyle\s*=\s*['"]""", re.IGNORECASE)
    violations = []

    for template_file in TEMPLATES_DIR.rglob("*.html"):
        content = template_file.read_text(encoding="utf-8")
        matches = list(style_attr_pattern.finditer(content))
        if matches:
            violations.append(f"{template_file.relative_to(PROJECT_ROOT)} ({len(matches)} occurrences)")

    assert not violations, "Found inline style= attributes in templates:\n" + "\n".join(violations)


def test_u14_zero_inline_onclick_in_templates():
    """U-14: Zero inline onclick= attributes across all application templates."""
    onclick_pattern = re.compile(r"""\bonclick\s*=\s*['"]""", re.IGNORECASE)
    violations = []

    for template_file in TEMPLATES_DIR.rglob("*.html"):
        content = template_file.read_text(encoding="utf-8")
        matches = list(onclick_pattern.finditer(content))
        if matches:
            violations.append(f"{template_file.relative_to(PROJECT_ROOT)} ({len(matches)} occurrences)")

    assert not violations, "Found inline onclick= attributes in templates:\n" + "\n".join(violations)


def test_u01_zero_hex_colors_outside_tokens_in_core_css():
    """U-01: Zero hex color codes in base.css, components.css, utilities.css, fonts.css."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    core_css_files = [
        STATIC_DIR / "css" / "base.css",
        STATIC_DIR / "css" / "components.css",
        STATIC_DIR / "css" / "utilities.css",
        STATIC_DIR / "css" / "fonts.css",
    ]

    violations = []
    for css_file in core_css_files:
        assert css_file.exists(), f"Missing core CSS: {css_file}"
        content = css_file.read_text(encoding="utf-8")
        matches = hex_pattern.findall(content)
        if matches:
            violations.append(f"{css_file.name}: {matches}")

    assert not violations, "Raw hex colors found outside tokens.css:\n" + "\n".join(violations)


def test_u02_self_hosted_typography_vendored():
    """U-02: DM Sans and Syne woff2 files exist locally and are mapped with font-display: swap."""
    fonts_dir = STATIC_DIR / "fonts"
    assert fonts_dir.exists(), "fonts directory must exist"

    dm_sans_fonts = list(fonts_dir.glob("dm-sans-*.woff2"))
    syne_fonts = list(fonts_dir.glob("syne-*.woff2"))

    assert len(dm_sans_fonts) >= 4, f"Expected at least 4 DM Sans woff2 files, found {len(dm_sans_fonts)}"
    assert len(syne_fonts) >= 3, f"Expected at least 3 Syne woff2 files, found {len(syne_fonts)}"

    fonts_css = (STATIC_DIR / "css" / "fonts.css").read_text(encoding="utf-8")
    assert "font-display: swap" in fonts_css
    assert "DM Sans" in fonts_css
    assert "Syne" in fonts_css


def test_u03_vendored_bootstrap_and_fontawesome():
    """U-03: Bootstrap 5.3 and Font Awesome 6.4 vendored locally without CDN calls."""
    bootstrap_css = STATIC_DIR / "vendor" / "bootstrap" / "bootstrap.min.css"
    bootstrap_js = STATIC_DIR / "vendor" / "bootstrap" / "bootstrap.bundle.min.js"
    fa_css = STATIC_DIR / "vendor" / "fontawesome" / "css" / "all.min.css"
    fa_webfonts = STATIC_DIR / "vendor" / "fontawesome" / "webfonts"

    assert bootstrap_css.exists(), "Vendored Bootstrap CSS missing"
    assert bootstrap_js.exists(), "Vendored Bootstrap JS missing"
    assert fa_css.exists(), "Vendored Font Awesome CSS missing"
    assert fa_webfonts.exists() and any(fa_webfonts.iterdir()), "Vendored Font Awesome webfonts missing"


def test_u04_component_macro_rendering(app):
    """U-04: Component macros in templates/components/ render valid, accessible markup."""
    with app.test_request_context():
        # 1. status_badge
        tmpl = "{% from 'components/badges.html' import status_badge %}{{ status_badge('Scheduled') }}"
        rendered = render_template_string(tmpl)
        assert "badge-status" in rendered
        assert "Scheduled" in rendered

        # 2. page_header
        tmpl = (
            "{% from 'components/page_header.html' import page_header %}"
            "{{ page_header('Clinical Records', subtitle='Patient timeline', "
            "breadcrumbs=[{'label': 'Home', 'url': '/'}, {'label': 'Records'}]) }}"
        )
        rendered = render_template_string(tmpl)
        assert "Clinical Records" in rendered
        assert "Patient timeline" in rendered
        assert "aria-label=\"Breadcrumb\"" in rendered

        # 3. empty_state
        tmpl = (
            "{% from 'components/empty_state.html' import empty_state %}"
            "{{ empty_state('No Appointments', 'You have no scheduled bookings.', 'fa-calendar') }}"
        )
        rendered = render_template_string(tmpl)
        assert "No Appointments" in rendered
        assert "empty-state" in rendered

        # 4. stepper
        tmpl = (
            "{% from 'components/stepper.html' import stepper %}"
            "{{ stepper([{'number': 1, 'label': 'Select Doctor'}, {'number': 2, 'label': 'Pick Slot'}], active_step=1) }}"
        )
        rendered = render_template_string(tmpl)
        assert "hms-stepper" in rendered
        assert "aria-current=\"step\"" in rendered

        # 5. skeleton
        tmpl = (
            "{% from 'components/skeleton.html' import skeleton_table %}"
            "{{ skeleton_table(rows=2, cols=2) }}"
        )
        rendered = render_template_string(tmpl)
        assert "skeleton-box" in rendered
        assert "aria-busy=\"true\"" in rendered


def test_u05_layouts_have_brand_theme_toggle_csrf_logout(app):
    """U-05: Layouts render Hedgewar Hospital Care brand, dark mode toggle, and CSRF logout."""
    app_layout = (TEMPLATES_DIR / "layouts" / "app.html").read_text(encoding="utf-8")
    public_layout = (TEMPLATES_DIR / "layouts" / "public.html").read_text(encoding="utf-8")

    # Brand
    assert "Hedgewar Hospital Care" in app_layout
    assert "Hedgewar Hospital Care" in public_layout

    # Theme toggle
    assert "theme-toggle-btn" in app_layout
    assert "theme-toggle-btn" in public_layout

    # Accessible skip link
    assert "skip-link" in app_layout
    assert "skip-link" in public_layout

    # CSRF logout form
    assert "action=\"{{ url_for('auth.logout') }}\"" in app_layout
    assert "csrf_token" in app_layout
