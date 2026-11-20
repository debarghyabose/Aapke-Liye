"""
Relief claim PDF, built with fpdf2 and HarfBuzz text shaping so Bengali, Devanagari,
Tamil and Telugu conjuncts and vowel signs render correctly.

Each value is written in the Noto font of its main script; the other fonts are fallbacks,
so mixed text such as "রিনা দাস (Rina)" also renders. Swap the layout for the real state
form once Member 5 shares it.
"""
import io
import json
from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.fonts import FontFace
from PIL import Image, ImageOps

from ..config import FONTS_DIR, RULES_DIR
from .relief import inr

IST = ZoneInfo("Asia/Kolkata")
DISCLAIMER = "Estimated amount — subject to official verification"
FONTS = {"latin": "NotoSans", "devanagari": "NotoSansDevanagari",
         "bengali": "NotoSansBengali", "tamil": "NotoSansTamil", "telugu": "NotoSansTelugu"}
SCRIPTS = [(0x0900, 0x097F, "devanagari"), (0x0980, 0x09FF, "bengali"),
           (0x0B80, 0x0BFF, "tamil"), (0x0C00, 0x0C7F, "telugu")]
APPLICANT_FIELDS = [("name", "Applicant name"), ("phone", "Mobile number"),
                    ("village", "Village / Ward"), ("district", "District"), ("state", "State"),
                    ("disaster_type", "Disaster"), ("date_of_incident", "Date of incident"),
                    ("bank_account_available", "Bank account available")]
HEAD = FontFace(emphasis="BOLD", fill_color=(232, 238, 247))
BOLD = FontFace(family="latin", emphasis="BOLD")


@lru_cache
def labels() -> dict:
    return json.loads((RULES_DIR / "labels.json").read_text(encoding="utf-8"))


def category_label(cat: str) -> str:
    return labels()["categories"].get(cat) or str(cat).replace("_", " ").title()


def item_label(cat: str, item: str) -> str:
    return labels()["items"].get(f"{cat}.{item}") or str(item).replace("_", " ").capitalize()


def document_label(doc: str) -> str:
    return labels()["documents"].get(doc) or str(doc).replace("_", " ").capitalize()


def script_font(text) -> str:
    """The font family for the script most of the text is written in."""
    counts: dict[str, int] = {}
    for ch in str(text):
        for lo, hi, name in SCRIPTS:
            if lo <= ord(ch) <= hi:
                counts[name] = counts.get(name, 0) + 1
    return max(counts, key=counts.get) if counts else "latin"


def in_ist(dt: datetime | None) -> str:
    if not dt:
        return "—"
    if dt.tzinfo is None:          # stored as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d-%m-%Y %H:%M IST")


def display(key: str, value) -> str:
    if value in (None, "", []):
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if key == "date_of_incident":
        try:
            return date.fromisoformat(str(value)).strftime("%d-%m-%Y")
        except ValueError:
            return str(value)
    if key == "disaster_type":
        return str(value).replace("_", " ").capitalize()
    return str(value)


def checks(v: dict) -> str:
    """e.g. "GPS ✓ · Time ✓ · Damage 80%", or "Verification pending"."""
    if v.get("status") != "complete":
        return "Verification pending"
    parts = [f"{name} {'✓' if v[key] else '✗'}"
             for key, name in (("gps_ok", "GPS"), ("timestamp_ok", "Time")) if key in v]
    score = v.get("damage_score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        parts.append(f"Damage {round(score * 100)}%")
    return " · ".join(parts) or "Checked"


def thumbnail(data: bytes | None) -> Image.Image | None:
    if not data:
        return None
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        img.thumbnail((320, 320))
        return img.convert("RGB")
    except Exception:  # unreadable image: the row still shows its details
        return None


class ClaimPDF(FPDF):
    def __init__(self, claim_id: str, estimate: bool):
        super().__init__(format="A4")
        self.claim_id, self.estimate = claim_id, estimate
        for family, file in FONTS.items():
            self.add_font(family, "", FONTS_DIR / f"{file}-Regular.ttf")
            self.add_font(family, "B", FONTS_DIR / f"{file}-Bold.ttf")
        self.add_font("symbols", "", FONTS_DIR / "NotoSansSymbols2-Regular.ttf")  # ✓ ✗
        self.set_fallback_fonts([*FONTS, "symbols"], exact_match=False)
        self.set_text_shaping(True)
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=18)
        self.set_title(f"Relief claim {claim_id}")

    def footer(self):
        self.set_y(-12)
        self.set_font("latin", size=7.5)
        self.set_text_color(110)
        text = f"Claim {self.claim_id}  ·  Page {self.page_no()}"
        self.cell(0, 5, f"{DISCLAIMER}  ·  {text}" if self.estimate else text, align="C")
        self.set_text_color(0)

    def heading(self, text: str):
        self.ln(3)
        self.set_font("latin", "B", 11)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.set_font("latin", size=9)

    def para(self, text: str, size: float = 9, bold: bool = False, h: float = 5):
        self.set_font(script_font(text), "B" if bold else "", size)
        self.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")
        self.set_font("latin", size=9)

    def value_cell(self, row, text: str, **kwargs):
        row.cell(text, style=FontFace(family=script_font(text)), **kwargs)


def build_claim_pdf(claim, photo_bytes: dict[int, bytes] | None = None) -> bytes:
    """photo_bytes: decrypted photo files by photo id, for the thumbnails."""
    f = claim.fields or {}
    relief = claim.relief or {"lines": [], "unmatched": [], "total": 0}
    estimate = bool(relief.get("estimate_only"))
    pdf = ClaimPDF(claim.id, estimate)
    pdf.add_page()

    pdf.set_font("latin", "B", 15)
    pdf.cell(0, 9, "Application for Disaster Relief Assistance (SDRF)",
             new_x="LMARGIN", new_y="NEXT")
    language = labels()["languages"].get(claim.language, claim.language)
    pdf.para(f"Claim ID: {claim.id}   ·   Filed: {in_ist(claim.submitted_at)}   ·   "
             f"Language: {language}", size=9.5)
    if estimate:
        pdf.ln(2)
        pdf.set_draw_color(180, 90, 0)
        pdf.set_text_color(150, 60, 0)
        pdf.set_font("latin", "B", 9.5)
        pdf.multi_cell(0, 6, f"{DISCLAIMER}. Rates come from sample SDRF rules "
                             f"(version {relief.get('rules_version')}).",
                       border=1, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0)
        pdf.set_draw_color(0)

    pdf.heading("1. Applicant details")
    with pdf.table(col_widths=(50, 130), first_row_as_headings=False, line_height=6,
                   padding=1.5) as t:
        for key, label in APPLICANT_FIELDS:
            row = t.row()
            row.cell(label, style=BOLD)
            pdf.value_cell(row, display(key, f.get(key)))

    pdf.heading("2. Losses and assistance claimed (as per SDRF norms)")
    with pdf.table(col_widths=(34, 58, 14, 36, 38), headings_style=HEAD, line_height=5.5,
                   padding=1.5) as t:
        head = t.row()
        for text in ["Category", "Item", "Qty", "Rate (₹)", "Amount (₹)"]:
            head.cell(text)
        for ln in relief["lines"]:
            row = t.row()
            row.cell(category_label(ln["category"]))
            item = item_label(ln["category"], ln["item"])
            if ln.get("damage_percent") is not None:
                item += f" ({ln['damage_percent']:g}% damaged)"
            row.cell(item + (f"\n{ln['note']}" if ln.get("note") else ""))
            row.cell(f"{ln['quantity']:g}", align="R")
            row.cell(f"{inr(ln['rate'])} {ln.get('unit', '')}".strip(), align="R")
            row.cell(inr(ln["amount"]), align="R")
        total = t.row()
        total.cell("Total (estimated)" if estimate else "Total", colspan=4, align="R", style=BOLD)
        total.cell(f"₹ {inr(relief['total'])}", align="R", style=BOLD)
    if relief.get("unmatched"):
        pdf.ln(1)
        pdf.para("Losses reported but not matched to an SDRF norm (for official review):",
                 bold=True)
        for u in relief["unmatched"]:
            pdf.para(f"•  {u.get('category') or '—'} / {u.get('item') or '—'}, "
                     f"quantity {u.get('quantity', '—')}: {u['reason']}")

    vault = getattr(claim, "documents_in_vault", None) or []
    if vault or claim.proof_suggestions:
        pdf.heading("3. Documents lost and substitute proof offered")
    if vault:
        pdf.para("Available in the family's document vault (saved before the disaster), "
                 "so these are not lost:", bold=True)
        with pdf.table(col_widths=(50, 130), headings_style=HEAD, line_height=5.5,
                       padding=1.5) as t:
            head = t.row()
            head.cell("Document")
            head.cell("Where it came from")
            for d in vault:
                row = t.row()
                row.cell(document_label(d["document"]))
                row.cell("DigiLocker (demo): sample document for demonstration only, "
                         "not issued by DigiLocker" if d["source"] == "digilocker_mock"
                         else "Available in vault: uploaded by the family")
    if claim.proof_suggestions:
        with pdf.table(col_widths=(50, 130), headings_style=HEAD, line_height=5.5,
                       padding=1.5) as t:
            head = t.row()
            head.cell("Document lost")
            head.cell("Substitute proof accepted")
            for p in claim.proof_suggestions:
                row = t.row()
                row.cell(document_label(p["document"]))
                row.cell("\n".join(f"•  {a}" for a in p["alternatives"]))

    pdf.heading("4. Photo evidence")
    if not claim.photos:
        pdf.para("No photos were attached to this claim.")
    else:
        with pdf.table(col_widths=(8, 32, 42, 40, 58), headings_style=HEAD, line_height=5.5,
                       padding=1.5, v_align="MIDDLE") as t:
            head = t.row()
            for text in ["#", "Photo", "Location (GPS)", "Taken at", "Checks"]:
                head.cell(text)
            for i, ph in enumerate(claim.photos, 1):
                row = t.row()
                row.cell(str(i))
                img = thumbnail((photo_bytes or {}).get(ph.id))
                if img:
                    row.cell(img=img, img_fill_width=True)
                else:
                    row.cell("—")
                gps = (f"{ph.lat:.5f}, {ph.lon:.5f}"
                       if ph.lat is not None and ph.lon is not None else "—")
                row.cell(gps)
                row.cell(in_ist(ph.taken_at))
                row.cell(checks(ph.verification or {}))

    pdf.heading("5. Declaration and consent")
    consent = labels()["consent"].get(claim.consent_text_version)
    pdf.para("I declare that the information above is true to the best of my knowledge.")
    if consent:
        pdf.para(f"Consent statement: “{consent}”")
    pdf.para(f"Consent recorded on {in_ist(claim.consent_given_at)}, consent text version "
             f"{claim.consent_text_version}.")

    if pdf.get_y() > 235:
        pdf.add_page()
    pdf.ln(6)
    y, w, h = pdf.get_y(), 85, 32
    for x, label in [(15, "Signature / Thumb impression of applicant"),
                     (110, "Verified by (Panchayat / Revenue officer)\nName, designation, seal, date")]:
        pdf.rect(x, y, w, h)
        pdf.set_xy(x + 2, y + h - 11)
        pdf.set_font("latin", size=8)
        pdf.multi_cell(w - 4, 4.5, label)
    return bytes(pdf.output())
