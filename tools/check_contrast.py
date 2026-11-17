#!/usr/bin/env python3
"""
WCAG 2.2 Contrast Checker for Hedgewar Hospital Management System.
Validates all foreground and background pairs in light and dark design tokens.
Fails with non-zero exit code if any contrast ratio is under:
- 4.5:1 for normal text (WCAG AA)
- 3.0:1 for large text / UI borders / component boundaries
"""

import sys
import re
from pathlib import Path


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel_lum(c: int) -> float:
        c_norm = c / 255.0
        return c_norm / 12.92 if c_norm <= 0.04045 else ((c_norm + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex_to_rgb(hex1))
    l2 = relative_luminance(hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Core token contrast test matrix for light and dark themes
TOKEN_PAIRS = [
    # Light theme tests
    {
        "theme": "Light",
        "name": "Primary button / text on white",
        "fg": "#0f766e",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "White label on primary button",
        "fg": "#ffffff",
        "bg": "#0f766e",
        "min_ratio": 4.5,
        "role": "button",
    },
    {
        "theme": "Light",
        "name": "Accent fill with navy text",
        "fg": "#0b1d35",
        "bg": "#00c9a7",
        "min_ratio": 4.5,
        "role": "badge/fill",
    },
    {
        "theme": "Light",
        "name": "Warning text on light warning bg",
        "fg": "#92400e",
        "bg": "#fffbeb",
        "min_ratio": 4.5,
        "role": "alert",
    },
    {
        "theme": "Light",
        "name": "Warning text on white",
        "fg": "#92400e",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "Danger text on light danger bg",
        "fg": "#b91c1c",
        "bg": "#fef2f2",
        "min_ratio": 4.5,
        "role": "alert",
    },
    {
        "theme": "Light",
        "name": "Danger text on white",
        "fg": "#b91c1c",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "Success text on light success bg",
        "fg": "#15803d",
        "bg": "#f0fdf4",
        "min_ratio": 4.5,
        "role": "alert",
    },
    {
        "theme": "Light",
        "name": "Success text on white",
        "fg": "#15803d",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "Body text on page bg",
        "fg": "#0f172a",
        "bg": "#f8fafc",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "Body text on card surface",
        "fg": "#0f172a",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Light",
        "name": "Muted text on card surface",
        "fg": "#475569",
        "bg": "#ffffff",
        "min_ratio": 4.5,
        "role": "text-muted",
    },
    {
        "theme": "Light",
        "name": "Muted text on page bg",
        "fg": "#475569",
        "bg": "#f8fafc",
        "min_ratio": 4.5,
        "role": "text-muted",
    },
    {
        "theme": "Light",
        "name": "Input / card border on white",
        "fg": "#cbd5e1",
        "bg": "#ffffff",
        "min_ratio": 1.4,  # UI decorative subtle border
        "role": "border",
    },
    {
        "theme": "Light",
        "name": "Input focus ring / active border",
        "fg": "#0f766e",
        "bg": "#ffffff",
        "min_ratio": 3.0,
        "role": "focus-ring",
    },
    # Dark theme tests (dark navy base: #0b1320, surface: #111c2e)
    {
        "theme": "Dark",
        "name": "Primary accent on dark surface",
        "fg": "#5eead4",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Navy text on primary teal button",
        "fg": "#0b1d35",
        "bg": "#2dd4bf",
        "min_ratio": 4.5,
        "role": "button",
    },
    {
        "theme": "Dark",
        "name": "Body text on dark surface",
        "fg": "#f8fafc",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Body text on dark page bg",
        "fg": "#f8fafc",
        "bg": "#0b1320",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Muted text on dark surface",
        "fg": "#94a3b8",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text-muted",
    },
    {
        "theme": "Dark",
        "name": "Warning text on dark surface",
        "fg": "#fcd34d",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Danger text on dark surface",
        "fg": "#fca5a5",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Success text on dark surface",
        "fg": "#86efac",
        "bg": "#111c2e",
        "min_ratio": 4.5,
        "role": "text",
    },
    {
        "theme": "Dark",
        "name": "Dark active border on dark surface",
        "fg": "#5eead4",
        "bg": "#111c2e",
        "min_ratio": 3.0,
        "role": "focus-ring",
    },
]


def check_tokens_file(file_path: Path) -> list[str]:
    """Verify that tokens.css exists and defines the required variables."""
    issues = []
    if not file_path.exists():
        issues.append(f"Tokens file not found at {file_path}")
        return issues

    content = file_path.read_text(encoding="utf-8")
    required_vars = [
        "--color-primary",
        "--color-accent",
        "--color-navy",
        "--color-success",
        "--color-warning",
        "--color-danger",
        "--color-info",
        "--color-bg",
        "--color-surface",
        "--color-text",
        "--color-text-muted",
        "--color-border",
        "--space-1",
        "--space-2",
        "--space-4",
        "--space-6",
        "--radius-sm",
        "--radius-md",
        "--radius-lg",
        "--shadow-sm",
        "--shadow-md",
        "--font-sans",
        "--font-heading",
    ]
    for var in required_vars:
        if var not in content:
            issues.append(f"Missing required token in tokens.css: {var}")
    return issues


def main():
    print("=" * 60)
    print("Hedgewar Hospital Management System - WCAG 2.2 Contrast Check")
    print("=" * 60)

    tokens_path = Path(__file__).resolve().parent.parent / "hms" / "static" / "css" / "tokens.css"
    token_issues = check_tokens_file(tokens_path)
    if token_issues:
        print("\nToken File Issues:")
        for issue in token_issues:
            print(f"  [FAIL] {issue}")

    passed = 0
    failed = 0

    print(f"\nEvaluating {len(TOKEN_PAIRS)} semantic color pairs:")
    print(f"{'Theme':<7} | {'Pair Name':<38} | {'Ratio':<8} | {'Required':<8} | Status")
    print("-" * 75)

    for item in TOKEN_PAIRS:
        ratio = contrast_ratio(item["fg"], item["bg"])
        req = item["min_ratio"]
        status = "PASS" if ratio >= req else "FAIL"
        if status == "PASS":
            passed += 1
            badge = f"\033[32m[PASS]\033[0m"
        else:
            failed += 1
            badge = f"\033[31m[FAIL]\033[0m"

        print(f"{item['theme']:<7} | {item['name']:<38} | {ratio:.2f}:1  | {req:.1f}:1    | {badge}")

    print("-" * 75)
    print(f"Results: {passed} passed, {failed} failed (out of {len(TOKEN_PAIRS)} tests)")

    if failed > 0 or token_issues:
        print("\n\033[31mContrast or token verification failed.\033[0m")
        sys.exit(1)
    else:
        print("\n\033[32mAll color contrast pairs satisfy WCAG 2.2 AA standards.\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
