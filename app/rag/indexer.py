from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict

logger = logging.getLogger("financial_research_agent.rag")

RAG_CHUNK_THRESHOLD = 1500

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
TOP_K_CHUNKS = 6

_STORE_CACHE_SIZE = 16
_store_cache: "OrderedDict[str, object]" = OrderedDict()

_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        import os

        from langchain_huggingface import HuggingFaceEmbeddings

        previously_set = "HF_HUB_OFFLINE" in os.environ
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        try:
            _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            if not previously_set:
                os.environ.pop("HF_HUB_OFFLINE", None)
            _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def warm_up() -> None:
    try:
        _get_embeddings()
    except Exception:  # noqa: BLE001
        logger.exception("RAG embeddings warm-up failed - first real call will load it instead")


def retrieve_relevant_text(document_text: str, query: str, max_chars: int) -> str:
    if len(document_text) <= max(RAG_CHUNK_THRESHOLD, max_chars):
        return document_text[:max_chars]

    from app.config import get_settings

    if not get_settings().rag_enabled:
        return document_text[:max_chars]

    try:
        return _rag_select(document_text, query, max_chars)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG chunk retrieval failed (%s); falling back to prefix truncation", exc)
        return document_text[:max_chars]


def _rag_select(document_text: str, query: str, max_chars: int) -> str:
    store, doc_count = _get_or_build_store(document_text)
    if store is None:
        return document_text[:max_chars]
    k = min(TOP_K_CHUNKS, doc_count)
    hits = store.similarity_search(query, k=k)

    selected_docs = []
    used = 0
    for doc in hits:
        text = doc.page_content
        if used + len(text) > max_chars:
            remaining = max_chars - used
            if remaining <= 0:
                break
            text = text[:remaining]
        selected_docs.append((doc.metadata.get("start_index", 0), text))
        used += len(text)
        if used >= max_chars:
            break

    selected_docs.sort(key=lambda item: item[0])
    pieces = [text for _start, text in selected_docs]
    selected = "\n[...]\n".join(pieces)
    logger.info(
        "RAG: %d chunks from %d-char document -> retrieved %d/%d chunks (%d chars) for query=%r",
        doc_count, len(document_text), len(pieces), k, len(selected), query[:60],
    )
    return selected


def _get_or_build_store(document_text: str):
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    key = hashlib.sha256(document_text.encode()).hexdigest()
    cached = _store_cache.get(key)
    if cached is not None:
        _store_cache.move_to_end(key)
        return cached

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    docs = splitter.create_documents([document_text])
    if not docs:
        return None, 0

    store = FAISS.from_documents(docs, _get_embeddings())
    result = (store, len(docs))
    _store_cache[key] = result
    _store_cache.move_to_end(key)
    if len(_store_cache) > _STORE_CACHE_SIZE:
        _store_cache.popitem(last=False)
    return result
