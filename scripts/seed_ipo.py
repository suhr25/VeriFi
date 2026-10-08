"""Seed (insert or update) one IPO's listing details and report text.

Every field here must come from the real, official IPO document - nothing
in this file is invented or estimated. Fill in IPOS below with the data
the user provides, then run:

    python -m scripts.seed_ipo

Re-running is safe: an IPO with the same ipo_id is updated in place, not
duplicated.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage.database import SessionLocal, init_db
from app.storage.models import IpoORM

DATA_DIR = Path(__file__).resolve().parent / "data"

# ---- SRIT India Limited -----------------------------------------------------
# Source: company DRHP/RHP (SEBI), NSE issue information, and press/financial
# database cross-checks (Economic Times, Moneycontrol, Business Standard,
# Groww, Trendlyne, StockAnalysis.com, Value Research, InvestorZone, IPO Bit,
# India Infoline, newboard.in) as supplied by the user. Figures are reported
# as given, not re-derived or estimated.

SRIT_FINANCIALS = [
    # Operating EBITDA excludes other income (offer-document basis).
    {"period": "FY23", "revenue_cr": 151.85, "operating_ebitda_cr": None, "operating_ebitda_margin_pct": None, "pat_cr": 15.04, "net_margin_pct": None, "eps": 5.55},
    {"period": "FY24", "revenue_cr": 271.09, "operating_ebitda_cr": 40.99, "operating_ebitda_margin_pct": 15.12, "pat_cr": 29.08, "net_margin_pct": 10.73, "eps": 10.79},
    {"period": "FY25", "revenue_cr": 389.35, "operating_ebitda_cr": 49.80, "operating_ebitda_margin_pct": 12.79, "pat_cr": 33.60, "net_margin_pct": 8.63, "eps": 8.32},
    {"period": "FY26", "revenue_cr": 450.00, "operating_ebitda_cr": 64.77, "operating_ebitda_margin_pct": 14.39, "pat_cr": 43.29, "net_margin_pct": 9.62, "eps": 9.12},
]

SRIT_BALANCE_SHEET = [
    {"period": "FY24", "total_assets_cr": 428.96, "net_worth_cr": 80.47, "borrowings_cr": 22.28, "debt_equity": None},
    {"period": "FY25", "total_assets_cr": 496.64, "net_worth_cr": 93.2, "borrowings_cr": 51.30, "debt_equity": 0.66},
    {"period": "FY26", "total_assets_cr": 614.16, "net_worth_cr": 193.27, "borrowings_cr": 36.15, "debt_equity": 0.23},
    {"period": "30 Jun 2026 (consolidated)", "total_assets_cr": None, "net_worth_cr": None, "borrowings_cr": 98.56, "debt_equity": None},
]

SRIT_CASH_FLOW = [
    {"period": "FY24", "cfo_cr": 34.16, "fcf_cr": 33.2},
    {"period": "FY25", "cfo_cr": 17.97, "fcf_cr": 6.8},
    {"period": "FY26", "cfo_cr": -12.10, "fcf_cr": -19.4},
]

SRIT_ORDER_BOOK = [
    {"period": "FY24", "order_book_cr": 1476.96},
    {"period": "FY25", "order_book_cr": 1216.06},
    {"period": "FY26", "order_book_cr": 1182.82},
    {"period": "30 Jun 2026", "order_book_cr": 1204.72},
]

SRIT_SEGMENTS = [
    {"period": "FY25", "segment": "e-Governance", "revenue_cr": 238.64, "pct": 61.29},
    {"period": "FY25", "segment": "Telecom & broadband", "revenue_cr": 91.03, "pct": 23.38},
    {"period": "FY25", "segment": "Healthcare", "revenue_cr": 59.68, "pct": 15.33},
    {"period": "FY26", "segment": "e-Governance", "revenue_cr": 307.76, "pct": 68.39},
    {"period": "FY26", "segment": "Telecom & broadband", "revenue_cr": 109.19, "pct": 24.27},
    {"period": "FY26", "segment": "Healthcare", "revenue_cr": 33.05, "pct": 7.34},
]

SRIT_VALUATION = [
    {"price": "₹123 (band low)", "market_cap_cr": 790.5, "pe": 18.3},
    {"price": "₹130 (IPO price)", "market_cap_cr": 835.5, "pe": 19.3},
    {"price": "₹148 (NSE listing open)", "market_cap_cr": 951.2, "pe": 22.0},
    {"price": "₹155 (listing day, later)", "market_cap_cr": 997, "pe": 23.0},
]

SRIT_SUBSCRIPTION = {
    "QIB": "91.84x", "NII": "312.99x", "Retail": "63.70x", "Overall": "125.16x",
}

SRIT_OBJECTS_OF_ISSUE = [
    {"use": "Working capital", "amount": "₹124.00 Cr"},
    {"use": "Product modernization / redevelopment", "amount": "₹12.86 Cr"},
    {"use": "Acquisitions, strategic initiatives, GCP", "amount": "Remaining amount"},
    {"use": "Issue expenses", "amount": "~₹26.42 Cr"},
]

SRIT_RISK_FACTORS = [
    "Heavy dependence on government contracts (~89% of FY26 revenue) exposes the company to tender delays, payment delays, budget approvals and administrative changes.",
    "High customer concentration: top 10 customers were ~89% of FY26 revenue (~92% in FY25); top 3 alone were ~71% in FY25.",
    "Operating cash flow turned negative in FY26 (-₹12.10 Cr) despite PAT of ₹43.29 Cr: about ₹385 Cr sits in government receivables and unbilled contract assets, with a ~176-day collection cycle.",
    "Order book has declined from ₹1,476.96 Cr (FY24) to ₹1,182.82 Cr (FY26) - existing orders are being converted into revenue faster than new orders are being added.",
    "Consolidated borrowings reported at ~₹98.56 Cr as of 30 June 2026, materially higher than the ₹36.15 Cr reported at FY26 year-end.",
    "Contingent liabilities of ~₹63.38 Cr, including bank guarantees and surety bonds, which could affect cash flow if invoked.",
    "MSME dues rose sharply: from ~₹23.4 lakh across 12 creditors (Sep 2025) to ~₹29.15 Cr across 53 creditors (Mar 2026).",
    "Tender-driven, largely L1 (lowest-bidder) pricing environment limits pricing power - the company won only 6 of 43 bids (~14%) in FY26.",
    "Past payment-related legal dispute connected to the Safe Kerala traffic enforcement project.",
    "Revenue growth has slowed sharply, from 43.63% (FY24 to FY25) to 15.57% (FY25 to FY26).",
]

SRIT_STRENGTHS = [
    "Revenue growth: ₹271 Cr → ₹450 Cr in two years.",
    "PAT growth: ₹29 Cr → ₹43 Cr, outpacing revenue growth in FY26.",
    "Order book of ₹1,200+ Cr provides meaningful revenue visibility (~2.6x FY26 revenue).",
    "Debt/equity improved to ~0.23x at FY26.",
    "~74% of clients were repeat clients in FY26.",
    "Government execution track record can act as a barrier to entry for smaller competitors.",
    "Recurring operations & maintenance revenue: roughly half of active orders have a recurring component.",
]

SRIT_CONCERNS = [
    "Cash flow: FY26 operating cash flow of -₹12.1 Cr against ₹43.3 Cr PAT - the single biggest concern.",
    "Working capital of ~₹150 Cr (up from ~₹33 Cr in FY24) is about a third of revenue.",
    "Government dependence: ~89% of revenue.",
    "Customer concentration: top 10 customers ≈92% of FY25 revenue.",
    "Order book declining: ₹1,477 Cr (FY24) → ₹1,183 Cr (FY26).",
    "Current borrowings (June 2026, consolidated) reported ~₹98.56 Cr, well above the FY26 year-end figure.",
    "Contingent liabilities of ~₹63.38 Cr.",
    "Tender-driven business model with limited pricing power.",
]

SRIT_VERDICT = {
    "Source": "Opinion from the third-party write-up this data was taken from - not from the offer document",
    "Business quality": "7/10 - good business, but concentrated and tender-driven",
    "Growth": "8/10 - strong historical growth",
    "Balance sheet": "7.5/10 - FY26 looks good, although June 2026 debt needs monitoring",
    "Profitability": "7/10 - healthy but not exceptional",
    "Cash-flow quality": "4/10 - the weak point",
    "Order-book quality": "6.5/10 - large, but declining",
    "IPO valuation at Rs 130": "6.5/10 - reasonable, not screamingly cheap",
    "Valuation at ~Rs 155 (post-listing)": "5.5-6/10 - less attractive as valuation has expanded",
    "Takeaway": (
        "Do not analyse SRIT India like a normal IT/software company - the more accurate mental model is a "
        "government technology systems integrator and project execution company with a significant "
        "working-capital financing requirement. Headline numbers (Rs 450 Cr revenue, Rs 43 Cr PAT, Rs 1,200+ Cr "
        "order book) look attractive, but PAT of Rs 43 Cr against operating cash flow of -Rs 12 Cr is the "
        "central investment question. If SRIT converts accounting profit into cash, the stock could justify a "
        "higher valuation; if profit stays trapped in working capital, the headline P/E can be misleading."
    ),
}

IPOS: list[dict] = [
    {
        "ipo_id": "ipo_srit_india",
        "company_name": "SRIT India Limited",
        "symbol": "SRIT",
        "board": "mainboard",
        "status": "listed",
        "exchange": "NSE+BSE",
        "open_date": date(2026, 9, 28),
        "close_date": date(2026, 9, 30),
        "listing_date": date(2026, 10, 6),
        "price_band_low": 123,
        "price_band_high": 130,
        "lot_size": 115,
        "face_value": 5,
        "issue_size_cr": 218.40,
        "fresh_issue_cr": 218.40,
        "ofs_cr": 0,
        "registrar": "KFin Technologies",
        "lead_managers": ["Choice Capital Advisors"],
        "about": (
            "SRIT India Limited is a Bengaluru-based government-focused technology systems integrator, executing "
            "large projects spanning software, hardware, implementation, support and operations across three "
            "segments: e-Governance, Telecommunications & broadband, and Healthcare technology. In FY26, "
            "approximately 89.41% of revenue came from government customers and 10.59% from enterprise "
            "customers. The 100% book-built mainboard IPO (28-30 Sep 2026, listed 6 Oct 2026) was subscribed "
            "125.16x overall (QIB 91.84x, NII 312.99x, Retail 63.70x)."
        ),
        "report_text": (DATA_DIR / "srit_india_report.md").read_text(encoding="utf-8"),
        "payload": {
            "financials": SRIT_FINANCIALS,
            "balance_sheet": SRIT_BALANCE_SHEET,
            "cash_flow": SRIT_CASH_FLOW,
            "order_book": SRIT_ORDER_BOOK,
            "segments": SRIT_SEGMENTS,
            "valuation": SRIT_VALUATION,
            "subscription": SRIT_SUBSCRIPTION,
            "objects_of_issue": SRIT_OBJECTS_OF_ISSUE,
            "strengths": SRIT_STRENGTHS,
            "concerns": SRIT_CONCERNS,
            "risk_factors": SRIT_RISK_FACTORS,
            "verdict": SRIT_VERDICT,
        },
    },
]

# -----------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        for data in IPOS:
            row = db.get(IpoORM, data["ipo_id"])
            now = _now()
            if row is None:
                row = IpoORM(ipo_id=data["ipo_id"], created_at=now)
                db.add(row)
            for field in (
                "company_name", "symbol", "board", "status", "exchange", "open_date", "close_date",
                "listing_date", "price_band_low", "price_band_high", "lot_size", "face_value",
                "issue_size_cr", "fresh_issue_cr", "ofs_cr", "registrar", "lead_managers", "about",
                "report_text", "payload",
            ):
                if field in data:
                    setattr(row, field, data[field])
            row.updated_at = now
        db.commit()
        print(f"Seeded {len(IPOS)} IPO(s).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
