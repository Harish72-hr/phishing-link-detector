"""Explainable URL heuristics. Rules contribute risk; they do not decide alone."""
from __future__ import annotations

from .feature_extractor import extract_features


def analyze_url(url: str) -> list[dict[str, str | int]]:
    features = extract_features(url)
    issues: list[dict[str, str | int]] = []

    def add(name: str, severity: str, explanation: str, score: int) -> None:
        issues.append({"name": name, "severity": severity, "explanation": explanation, "score": score})

    if features["has_ip_address"]:
        add("IP-based host", "High", "The URL uses a numeric IP address instead of a recognizable domain.", 24)
    if features["url_length"] > 100:
        add("Excessive URL length", "Medium", "Long URLs can hide the destination and are common in phishing campaigns.", 10)
    if features["has_at_symbol"]:
        add("Misleading @ symbol", "High", "An @ symbol can obscure the actual host a browser will contact.", 20)
    if features["suspicious_keyword_count"]:
        add("Suspicious keyword", "Medium", "The URL contains account, verification, payment, or other phishing-associated language.", 12)
    if features["subdomain_count"] > 2:
        add("Nested subdomains", "Medium", "Multiple subdomains can imitate a trusted organization or conceal the registrable domain.", 10)
    if not features["uses_https"]:
        add("No HTTPS", "Low", "The URL does not use encrypted HTTPS transport. HTTP alone is not proof of phishing.", 5)
    if features["special_char_count"] > 5:
        add("Unusual special characters", "Medium", "The URL contains an unusually high number of special characters.", 9)
    if features["is_shortened"]:
        add("URL shortener", "Medium", "A shortening service hides the final destination until the link is opened.", 12)
    if features["suspicious_tld"]:
        add("Suspicious TLD", "Medium", "This top-level domain is frequently abused in disposable or deceptive registrations.", 10)
    if features["double_slash_count"]:
        add("Double slash in path", "Low", "An extra slash after the host can be used to make a URL appear more trustworthy.", 6)
    return issues
