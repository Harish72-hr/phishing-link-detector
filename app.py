from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from database.database import create_scan, dashboard_stats, get_scan, init_db, list_scans
from reports.report_generator import create_report
from scanner.feature_extractor import extract_features
from scanner.ml_detector import ModelUnavailableError, predict_url
from scanner.risk_engine import assess_risk
from scanner.rule_engine import analyze_url

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "phishguard-development-key"),
    DATABASE_PATH=str(BASE_DIR / os.getenv("DATABASE_PATH", "database/phishguard.db")),
    MODEL_PATH=str(BASE_DIR / os.getenv("MODEL_PATH", "model/phishing_model.pkl")),
    FEATURES_PATH=str(BASE_DIR / os.getenv("FEATURES_PATH", "model/feature_names.json")),
)
init_db(app.config["DATABASE_PATH"])


def valid_url(value: str) -> bool:
    if len(value) > 2048 or re.search(r"[\s<>\"']", value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def row_to_scan(row):
    data = dict(row)
    data["issues"] = json.loads(data["issues"])
    data["features"] = json.loads(data["features"])
    data["confidence"] = f"{float(data['confidence']) * 100:.1f}%"
    return data


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    value = request.form.get("url", "").strip()
    if not valid_url(value):
        flash("Enter a complete, valid HTTP or HTTPS URL.", "error")
        return redirect(url_for("index"))
    issues = analyze_url(value)
    try:
        model_result = predict_url(value, app.config["MODEL_PATH"], app.config["FEATURES_PATH"])
        prediction = model_result["prediction"]  # "Phishing" or "Legitimate"
        # Random Forest vote-fraction confidence is not a calibrated probability.
        # Cap at 0.99 so the UI never claims absolute certainty, which would be misleading.
        confidence = min(float(model_result["confidence"]), 0.99)
    except ModelUnavailableError as error:
        model_result = None
        prediction = "Unclassified"
        confidence = 0.0
        flash(str(error), "warning")
    risk = assess_risk(model_result, issues)
    scan_id = create_scan(app.config["DATABASE_PATH"], {"url": value, "prediction": prediction, "confidence": confidence, "risk_score": risk["score"], "risk_level": risk["level"], "issues": issues, "features": extract_features(value)})
    return redirect(url_for("result", scan_id=scan_id))


@app.route("/result/<int:scan_id>")
def result(scan_id: int):
    row = get_scan(app.config["DATABASE_PATH"], scan_id)
    if row is None:
        abort(404)
    return render_template("result.html", scan=row_to_scan(row))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", stats=dashboard_stats(app.config["DATABASE_PATH"]))


@app.route("/history")
def history():
    search = request.args.get("q", "").strip()
    scans = [row_to_scan(row) for row in list_scans(app.config["DATABASE_PATH"], search)]
    return render_template("history.html", scans=scans, search=search)


@app.route("/download-report/<int:scan_id>")
def download_report(scan_id: int):
    row = get_scan(app.config["DATABASE_PATH"], scan_id)
    if row is None:
        abort(404)
    try:
        report = create_report(row_to_scan(row))
        return send_file(report, as_attachment=True, download_name=f"phishguard-report-{scan_id}.pdf", mimetype="application/pdf")
    except Exception:
        flash("The report could not be generated.", "error")
        return redirect(url_for("result", scan_id=scan_id))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)