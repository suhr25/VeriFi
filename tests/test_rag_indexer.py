import pytest

from app.rag.indexer import RAG_CHUNK_THRESHOLD, retrieve_relevant_text

_LONG_DOCUMENT = (
    "Overview: This filing excerpt covers the reporting period in detail.\n\n"
    + ("Segment performance in the Americas region showed steady demand across product lines. " * 12)
    + "\n\nFinancial Performance: Revenue was $85.8 billion for the quarter, net income was "
    "$21.4 billion, and operating margin was approximately 29.6% on a GAAP basis. Cash and cash "
    "equivalents totaled $28.4 billion at quarter end.\n\n"
    + ("Management discussion of routine operational matters and administrative updates. " * 12)
    + "\n\nRisk Factors: The Company faces substantial cybersecurity risk, including potential "
    "data breaches and disruption to operations from malicious actors. Supply chain "
    "concentration among single-source suppliers exposes the Company to geopolitical "
    "disruption. Regulatory scrutiny under antitrust and data-privacy law in multiple "
    "jurisdictions could increase compliance costs and restrict elements of the business.\n\n"
    + ("Further routine administrative and procedural filing content follows. " * 12)
)

assert len(_LONG_DOCUMENT) > RAG_CHUNK_THRESHOLD, "fixture must exceed the RAG trigger threshold"


def test_short_document_passes_through_unchanged():
    short = "Revenue was $10 million this quarter."
    result = retrieve_relevant_text(short, "revenue", max_chars=500)
    assert result == short


def test_retrieved_text_pieces_are_verbatim_substrings_of_the_source():
    result = retrieve_relevant_text(_LONG_DOCUMENT, "cybersecurity risk supply chain", max_chars=1000)
    for piece in result.split("\n[...]\n"):
        assert piece in _LONG_DOCUMENT, f"non-verbatim piece returned: {piece[:80]!r}"


def test_risk_query_retrieves_the_risk_factors_section():
    result = retrieve_relevant_text(
        _LONG_DOCUMENT, "cybersecurity data breach regulatory antitrust supply chain risk", max_chars=1400
    )
    assert "Risk Factors" in result or "cybersecurity" in result.lower()


def test_financial_query_retrieves_the_financial_section():
    result = retrieve_relevant_text(
        _LONG_DOCUMENT, "revenue net income operating margin cash", max_chars=1400
    )
    assert "85.8 billion" in result or "21.4 billion" in result


def test_different_queries_against_the_same_document_return_different_text():
    risk_result = retrieve_relevant_text(_LONG_DOCUMENT, "cybersecurity regulatory risk", max_chars=900)
    revenue_result = retrieve_relevant_text(_LONG_DOCUMENT, "revenue net income margin", max_chars=900)
    assert risk_result != revenue_result


def test_result_respects_the_max_chars_budget():
    result = retrieve_relevant_text(_LONG_DOCUMENT, "risk", max_chars=400)
    assert len(result) <= 400 + len("\n[...]\n") * 3


def test_rag_failure_falls_back_to_prefix_truncation(monkeypatch):
    import app.rag.indexer as indexer_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated embedding failure")

    monkeypatch.setattr(indexer_module, "_rag_select", _boom)
    result = retrieve_relevant_text(_LONG_DOCUMENT, "risk", max_chars=200)
    assert result == _LONG_DOCUMENT[:200]
