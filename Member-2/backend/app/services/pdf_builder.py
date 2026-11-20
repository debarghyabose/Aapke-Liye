"""Builds the relief claim PDF. Swap the layout for the real state form once Member 5 shares it."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import STORAGE_DIR

LABELS = {
    "name": "Applicant name", "phone": "Phone", "village": "Village / Ward",
    "district": "District", "state": "State", "disaster_type": "Disaster",
    "date_of_incident": "Date of incident",
}


def _table(rows, widths):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ]))
    return t


def build_claim_pdf(claim) -> Path:
    out = STORAGE_DIR / "pdfs" / f"{claim.id}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    s = getSampleStyleSheet()
    f = claim.fields or {}
    story = [
        Paragraph("Application for Disaster Relief Assistance (SDRF)", s["Title"]),
        Paragraph(f"Claim ID: <b>{claim.id}</b> &nbsp;&nbsp; Filed: "
                  f"{datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M')} IST &nbsp;&nbsp; Language: {claim.language}",
                  s["Normal"]),
        Spacer(1, 6 * mm),
        Paragraph("1. Applicant details", s["Heading2"]),
        _table([["Field", "Value"]] + [[lbl, str(f.get(k) or "—")] for k, lbl in LABELS.items()],
               [55 * mm, 115 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("2. Losses and assistance claimed (as per SDRF norms)", s["Heading2"]),
    ]

    relief = claim.relief or {"lines": [], "total": 0}
    rows = [["Category", "Item", "Qty", "Rate (Rs.)", "Amount (Rs.)"]]
    for ln in relief["lines"]:
        rows.append([ln["category"], ln["item"].replace("_", " "), f"{ln['quantity']:g}",
                     f"{ln['rate']:,}", f"{ln['amount']:,}"])
    rows.append(["", "", "", "Total", f"{relief['total']:,}"])
    story += [_table(rows, [28 * mm, 55 * mm, 17 * mm, 30 * mm, 40 * mm]), Spacer(1, 4 * mm)]

    if claim.proof_suggestions:
        story.append(Paragraph("3. Documents lost and substitute proof offered", s["Heading2"]))
        for p in claim.proof_suggestions:
            story.append(Paragraph(f"<b>{p['document']}</b>: " + "; ".join(p["alternatives"]), s["Normal"]))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("4. Photo evidence", s["Heading2"]))
    prow = [["#", "GPS", "Taken at", "Damage score", "Checks"]]
    for i, ph in enumerate(claim.photos, 1):
        v = ph.verification or {}
        checks = ", ".join(k for k in ("gps_ok", "timestamp_ok") if v.get(k)) or "—"
        if v.get("duplicate"):
            checks += " | DUPLICATE"
        gps = f"{ph.lat:.5f}, {ph.lon:.5f}" if ph.lat is not None and ph.lon is not None else "—"
        prow.append([str(i), gps, ph.taken_at or "—", str(v.get("damage_score", "—")), checks])
    story += [_table(prow, [10 * mm, 45 * mm, 45 * mm, 28 * mm, 42 * mm]), Spacer(1, 6 * mm)]

    story += [
        Paragraph("Declaration: I declare that the information above is true to the best of my "
                  "knowledge. I consent to its use for processing this relief claim.", s["Normal"]),
        Spacer(1, 14 * mm),
        Paragraph("Signature / Thumb impression of applicant ____________________ "
                  "&nbsp;&nbsp; Verified by (Panchayat / Revenue officer) ____________________",
                  s["Normal"]),
    ]
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=15 * mm, bottomMargin=15 * mm, title=f"Relief claim {claim.id}").build(story)
    return out
