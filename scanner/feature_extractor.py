"""Deterministic URL feature extraction shared by training and prediction."""
from __future__ import annotations

import ipaddress
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlsplit

FEATURE_NAMES = [
    "url_length", "domain_length", "path_length", "dot_count", "hyphen_count",
    "underscore_count", "special_char_count", "digit_count", "subdomain_count",
    "parameter_count", "path_segment_count", "has_at_symbol", "has_ip_address",
    "uses_https", "suspicious_keyword_count", "is_shortened", "suspicious_tld",
    "double_slash_count", "digit_ratio", "domain_entropy",
]

SUSPICIOUS_KEYWORDS = {
    "login", "signin", "verify", "verification", "secure", "account", "update",
    "password", "confirm", "bank", "payment", "wallet", "recover", "unlock",
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly", "cutt.ly"}
SUSPICIOUS_TLDS = {".zip", ".mov", ".click", ".top", ".xyz", ".work", ".gq", ".tk", ".ml", ".cf"}


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return round(-sum((count / length) * math.log2(count / length) for count in counts.values()), 4)


def _is_ip(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        return True
    except ValueError:
        return False


def extract_features(url: str) -> dict[str, float | int]:
    """Return the stable, numeric feature vector used by the model."""
    value = (url or "").strip()
    parsed = urlsplit(value if "://" in value else f"http://{value}")
    domain = (parsed.hostname or "").lower()
    path = parsed.path or ""
    lowered = value.lower()
    domain_parts = [part for part in domain.split(".") if part]
    keywords = sum(1 for keyword in SUSPICIOUS_KEYWORDS if keyword in lowered)
    special_count = len(re.findall(r"[^a-zA-Z0-9./:_-]", value))
    digit_count = sum(character.isdigit() for character in value)
    tld_match = any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS)
    return {
        "url_length": len(value),
        "domain_length": len(domain),
        "path_length": len(path),
        "dot_count": value.count("."),
        "hyphen_count": value.count("-"),
        "underscore_count": value.count("_"),
        "special_char_count": special_count,
        "digit_count": digit_count,
        "subdomain_count": max(0, len(domain_parts) - 2),
        "parameter_count": len(parse_qsl(parsed.query, keep_blank_values=True)),
        "path_segment_count": len([segment for segment in path.split("/") if segment]),
        "has_at_symbol": int("@" in value),
        "has_ip_address": int(_is_ip(domain)),
        "uses_https": int(parsed.scheme.lower() == "https"),
        "suspicious_keyword_count": keywords,
        "is_shortened": int(domain in SHORTENERS or any(domain.endswith(f".{host}") for host in SHORTENERS)),
        "suspicious_tld": int(tld_match),
        "double_slash_count": max(0, value.count("//") - 1),
        "digit_ratio": round(digit_count / max(1, len(value)), 4),
        "domain_entropy": _entropy(domain),
    }


def feature_vector(url: str, feature_names: list[str] | None = None) -> list[float | int]:
    features = extract_features(url)
    names = feature_names or FEATURE_NAMES
    return [features[name] for name in names]
