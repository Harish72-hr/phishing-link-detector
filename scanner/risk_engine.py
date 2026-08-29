"""Combine model evidence and explainable rules into a bounded risk score."""
from __future__ import annotations


def assess_risk(model_result: dict[str, object] | None, issues: list[dict[str, object]]) -> dict[str, object]:
    # Rules contribute their documented weights; ML contributes up to 45 points.
    rule_score = sum(int(issue["score"]) for issue in issues)
    # ML score only added when model predicts phishing (label == 1)
    ml_score = round(float(model_result.get("confidence", 0)) * 45) if model_result and model_result.get("label") == 1 else 0
    score = min(100, rule_score + ml_score)
    if score >= 75:
        level = "Critical"
    elif score >= 50:
        level = "High"
    elif score >= 25:
        level = "Medium"
    else:
        level = "Low"
    return {"score": score, "level": level, "rule_score": rule_score, "ml_score": ml_score}
