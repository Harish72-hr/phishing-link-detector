from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def create_report(scan: dict[str, object]) -> BytesIO:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    story = [Paragraph("PhishGuard Security Report", styles["Title"]), Spacer(1, 14)]
    values = [[label, str(scan.get(key, ""))] for label, key in (("Scan timestamp", "created_at"), ("URL", "url"), ("Prediction", "prediction"), ("Confidence", "confidence"), ("Risk score", "risk_score"), ("Risk level", "risk_level"))]
    table = Table(values, colWidths=[125, 390])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef5")), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([table, Spacer(1, 16), Paragraph("Extracted URL features", styles["Heading2"])])
    for key, value in scan.get("features", {}).items():
        story.append(Paragraph(f"{key}: {value}", styles["BodyText"]))
    story.extend([Spacer(1, 12), Paragraph("Detected security issues", styles["Heading2"])])
    for issue in scan.get("issues", []):
        story.append(Paragraph(f"{issue['name']} ({issue['severity']}): {issue['explanation']}", styles["BodyText"]))
    story.extend([Spacer(1, 12), Paragraph("Recommendations", styles["Heading2"]), Paragraph("Do not enter passwords or financial information. Verify the domain manually and contact the organization through its official website.", styles["BodyText"]), Spacer(1, 12), Paragraph("Disclaimer: This automated analysis is not guaranteed and is not a replacement for professional threat intelligence.", styles["Italic"])])
    document.build(story)
    output.seek(0)
    return output
