"""PDF report generator for BhoomiSatya property verification reports."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Template
from weasyprint import HTML

logger = structlog.get_logger(__name__)

REPORTS_DIR = Path(os.getenv("BHOOMISATYA_REPORTS_DIR", "reports"))

REPORT_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>BhoomiSatya Report – {{ report_id }}</title>
<style>
  @page { size: A4; margin: 1.5cm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 11pt;
    color: #1a1a1a;
    line-height: 1.5;
  }
  .header {
    background: linear-gradient(135deg, #1a5276, #2e86c1);
    color: white;
    padding: 24px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 4px;
    margin-bottom: 20px;
  }
  .header h1 { font-size: 22pt; font-weight: 700; }
  .header .subtitle { font-size: 10pt; opacity: 0.85; }
  .header .report-meta { text-align: right; font-size: 9pt; }

  .section { margin-bottom: 18px; page-break-inside: avoid; }
  .section-title {
    font-size: 13pt;
    font-weight: 600;
    color: #1a5276;
    border-bottom: 2px solid #2e86c1;
    padding-bottom: 4px;
    margin-bottom: 10px;
  }

  /* Trust score gauge */
  .score-container { text-align: center; margin: 16px 0; }
  .score-gauge {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 32pt;
    font-weight: 700;
    color: white;
    border: 6px solid rgba(0,0,0,0.1);
  }
  .score-safe { background: #27ae60; }
  .score-caution { background: #f39c12; }
  .score-unsafe { background: #e74c3c; }
  .score-label {
    font-size: 11pt;
    font-weight: 600;
    margin-top: 6px;
  }

  /* Verdict badge */
  .verdict-badge {
    display: inline-block;
    padding: 4px 16px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 11pt;
    color: white;
  }
  .verdict-safe { background: #27ae60; }
  .verdict-caution { background: #f39c12; }
  .verdict-unsafe { background: #e74c3c; }

  .verdict-fair { background: #27ae60; }
  .verdict-overpriced { background: #e74c3c; }
  .verdict-underpriced { background: #f39c12; }
  .verdict-nodata { background: #95a5a6; }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 10pt;
  }
  th, td {
    border: 1px solid #d5d8dc;
    padding: 6px 10px;
    text-align: left;
  }
  th { background: #eaf2f8; color: #1a5276; font-weight: 600; }
  tr:nth-child(even) { background: #f9fafb; }

  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 20px;
  }
  .detail-grid .label { color: #666; font-size: 9pt; }
  .detail-grid .value { font-weight: 500; }

  .satellite-img { max-width: 100%; border: 1px solid #ccc; border-radius: 4px; margin: 8px 0; }

  .disclaimer {
    margin-top: 24px;
    padding: 12px;
    background: #fef9e7;
    border-left: 4px solid #f39c12;
    font-size: 9pt;
    color: #7d6608;
  }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div>
    <h1>BhoomiSatya</h1>
    <div class="subtitle">AI-Powered Property Verification Report</div>
  </div>
  <div class="report-meta">
    Report ID: {{ report_id }}<br>
    Date: {{ generated_date }}
  </div>
</div>

<!-- Property Details -->
<div class="section">
  <div class="section-title">Property Details</div>
  <div class="detail-grid">
    <div><span class="label">Survey / Plot No.</span><br><span class="value">{{ prop.survey_number or 'N/A' }}</span></div>
    <div><span class="label">State</span><br><span class="value">{{ prop.state or 'N/A' }}</span></div>
    <div><span class="label">District</span><br><span class="value">{{ prop.district or 'N/A' }}</span></div>
    <div><span class="label">Mandal</span><br><span class="value">{{ prop.mandal or 'N/A' }}</span></div>
    <div><span class="label">Village</span><br><span class="value">{{ prop.village or 'N/A' }}</span></div>
    <div><span class="label">Owner</span><br><span class="value">{{ prop.owner_name or 'N/A' }}</span></div>
    <div><span class="label">Project</span><br><span class="value">{{ prop.project_name or 'N/A' }}</span></div>
    <div><span class="label">Asking Price</span><br><span class="value">{{ prop.asking_price or 'N/A' }}</span></div>
  </div>
</div>

<!-- Safety Score -->
<div class="section">
  <div class="section-title">Safety Assessment</div>
  <div class="score-container">
    <div class="score-gauge {{ score_class }}">{{ trust_score }}</div>
    <div class="score-label">Trust Score out of 100</div>
  </div>
  <p style="text-align:center; margin-top: 8px;">
    Safety Verdict:
    <span class="verdict-badge {{ verdict_class }}">{{ safety_verdict }}</span>
  </p>
</div>

<!-- Findings -->
{% if findings %}
<div class="section">
  <div class="section-title">Findings</div>
  <table>
    <thead><tr><th>Category</th><th>Finding</th><th>Severity</th><th>Source</th></tr></thead>
    <tbody>
    {% for f in findings %}
      <tr>
        <td>{{ f.category }}</td>
        <td>{{ f.finding }}</td>
        <td>{{ f.severity }}</td>
        <td>{{ f.source }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<!-- Valuation Analysis -->
<div class="section">
  <div class="section-title">Valuation Analysis</div>
  <p>
    Price Verdict:
    <span class="verdict-badge {{ price_verdict_class }}">{{ valuation_verdict }}</span>
  </p>
  {% if guideline_value %}
  <p style="margin-top:8px;"><strong>Guideline Value:</strong> ₹{{ guideline_value }} per sq. yard</p>
  {% endif %}
  {% if fair_market_range %}
  <p><strong>Estimated Fair Market Range:</strong> ₹{{ fair_market_range.low }} – ₹{{ fair_market_range.high }}</p>
  {% endif %}
  {% if comparable_sales %}
  <table style="margin-top:10px;">
    <thead><tr><th>Location</th><th>Area</th><th>Sale Price (₹)</th><th>Date</th></tr></thead>
    <tbody>
    {% for s in comparable_sales %}
      <tr><td>{{ s.location }}</td><td>{{ s.area }}</td><td>{{ s.sale_price }}</td><td>{{ s.date }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
  {% if valuation_analysis %}
  <p style="margin-top:8px;">{{ valuation_analysis }}</p>
  {% endif %}
</div>

<!-- Satellite Image -->
{% if satellite_image_url %}
<div class="section">
  <div class="section-title">Satellite / Land Use Data</div>
  <img class="satellite-img" src="{{ satellite_image_url }}" alt="Satellite view">
</div>
{% endif %}

<!-- Disclaimer -->
<div class="disclaimer">
  <strong>Disclaimer:</strong> This report is generated by BhoomiSatya using
  publicly available government data and AI analysis. It does not constitute
  legal advice. Always verify findings with a qualified legal professional
  and conduct an independent physical inspection before making purchase
  decisions. Data accuracy depends on the availability and correctness of
  government portal records at the time of retrieval.
</div>

</body>
</html>
"""


def _score_css_class(score: int) -> str:
    if score >= 80:
        return "score-safe"
    if score >= 50:
        return "score-caution"
    return "score-unsafe"


def _verdict_css_class(verdict: str) -> str:
    return {
        "SAFE": "verdict-safe",
        "CAUTION": "verdict-caution",
        "UNSAFE": "verdict-unsafe",
    }.get(verdict, "verdict-caution")


def _price_verdict_css_class(verdict: str) -> str:
    return {
        "FAIR_PRICE": "verdict-fair",
        "OVERPRICED": "verdict-overpriced",
        "UNDERPRICED": "verdict-underpriced",
        "INSUFFICIENT_DATA": "verdict-nodata",
    }.get(verdict, "verdict-nodata")


async def generate_pdf(report_data: dict[str, Any]) -> bytes:
    """Render the verification report as a PDF.

    Args:
        report_data: Dict containing property_input, trust_score,
            safety_verdict, valuation_verdict, and raw data sections.

    Returns:
        PDF file contents as bytes.
    """
    log = logger.bind(report_id=report_data.get("report_id"))
    log.info("rendering_pdf")

    prop = report_data.get("property_input", {})
    trust_score = report_data.get("trust_score", 0)
    safety_verdict = report_data.get("safety_verdict", "CAUTION")
    valuation_verdict = report_data.get("valuation_verdict", "INSUFFICIENT_DATA")

    # Extract structured analysis fields if present
    messages = report_data.get("messages", [])
    analysis: dict[str, Any] = {}
    for msg in messages:
        if isinstance(msg, dict) and "analysis" in msg:
            analysis = msg["analysis"]
            break

    template = Template(REPORT_HTML_TEMPLATE)
    html_str = template.render(
        report_id=report_data.get("report_id", "N/A"),
        generated_date=datetime.utcnow().strftime("%d %b %Y, %H:%M UTC"),
        prop=prop,
        trust_score=trust_score,
        score_class=_score_css_class(trust_score),
        safety_verdict=safety_verdict,
        verdict_class=_verdict_css_class(safety_verdict),
        valuation_verdict=valuation_verdict,
        price_verdict_class=_price_verdict_css_class(valuation_verdict),
        findings=analysis.get("safety_findings", []),
        guideline_value=analysis.get("guideline_value_per_unit"),
        fair_market_range=analysis.get("estimated_fair_market_range"),
        comparable_sales=analysis.get("comparable_sales", []),
        valuation_analysis=analysis.get("valuation_analysis"),
        satellite_image_url=report_data.get("satellite_info", {}).get("image_url")
        if isinstance(report_data.get("satellite_info"), dict)
        else None,
    )

    pdf_bytes: bytes = HTML(string=html_str).write_pdf()  # type: ignore[assignment]
    log.info("pdf_rendered", size_bytes=len(pdf_bytes))
    return pdf_bytes


async def save_report(report_id: str, pdf_bytes: bytes) -> str:
    """Save a generated PDF report to disk.

    Args:
        report_id: Unique report identifier.
        pdf_bytes: PDF content.

    Returns:
        File path where the report was saved.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / f"{report_id}.pdf"
    file_path.write_bytes(pdf_bytes)
    logger.info("report_saved", path=str(file_path))
    return str(file_path)
