import csv
import json
import random
from pathlib import Path

import httpx
import numpy as np
import weave
from schemas import PitchDeck

DATA_DIR = Path(__file__).parent / "data"
CSV_PATH = DATA_DIR / "yc_companies.csv"
EMB_PATH = DATA_DIR / "yc_embeddings.npy"
VECTORIZER_PATH = DATA_DIR / "yc_vectorizer.joblib"
YC_API = "https://yc-oss.github.io/api/companies/all.json"
SAMPLE_SIZE = 500
TOP_K = 5
_EMBEDDING_BACKEND: str | None = None
_COMPANIES: list[dict[str, str]] | None = None
_EMBEDDINGS: np.ndarray | None = None
_VECTORIZER = None


def _normalize_status(raw: str | None) -> str:
    if not raw:
        return "unknown"
    return raw.strip().lower()


def _normalize_tags(raw) -> str:
    if isinstance(raw, list):
        return ", ".join(str(t) for t in raw)
    return str(raw or "")


def ensure_yc_dataset() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if CSV_PATH.exists():
        return

    resp = httpx.get(YC_API, timeout=120)
    resp.raise_for_status()
    companies = resp.json()
    rng = random.Random(42)
    sample = rng.sample(companies, min(SAMPLE_SIZE, len(companies)))

    rows = []
    for c in sample:
        rows.append(
            {
                "name": c.get("name") or "",
                "batch": c.get("batch") or "",
                "status": _normalize_status(c.get("status")),
                "one_liner": c.get("one_liner") or "",
                "long_description": c.get("long_description") or "",
                "tags": _normalize_tags(c.get("tags")),
            }
        )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "batch", "status", "one_liner", "long_description", "tags"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _load_companies() -> list[dict[str, str]]:
    global _COMPANIES
    ensure_yc_dataset()
    if _COMPANIES is None:
        with CSV_PATH.open(encoding="utf-8") as f:
            _COMPANIES = list(csv.DictReader(f))
    return _COMPANIES


def _doc_text(company: dict[str, str]) -> str:
    return f"{company['one_liner']} {company['long_description']}".strip()


def _embed_sentence_transformers(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    return np.asarray(model.encode(texts, show_progress_bar=False), dtype=np.float32)


def _embed_tfidf(texts: list[str]) -> tuple[np.ndarray, object]:
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(max_features=8000, stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    return matrix.toarray().astype(np.float32), vectorizer


def _ensure_embeddings() -> None:
    global _EMBEDDING_BACKEND, _EMBEDDINGS, _VECTORIZER

    if _EMBEDDINGS is not None:
        return

    companies = _load_companies()
    texts = [_doc_text(c) for c in companies]

    if EMB_PATH.exists():
        _EMBEDDINGS = np.load(EMB_PATH)
        meta_path = DATA_DIR / "yc_embed_meta.json"
        if meta_path.exists():
            _EMBEDDING_BACKEND = json.loads(meta_path.read_text())["backend"]
        if VECTORIZER_PATH.exists():
            import joblib

            _VECTORIZER = joblib.load(VECTORIZER_PATH)
        return

    try:
        _EMBEDDINGS = _embed_sentence_transformers(texts)
        _EMBEDDING_BACKEND = "sentence-transformers"
    except Exception:
        _EMBEDDINGS, _VECTORIZER = _embed_tfidf(texts)
        _EMBEDDING_BACKEND = "tfidf"
        import joblib

        joblib.dump(_VECTORIZER, VECTORIZER_PATH)

    np.save(EMB_PATH, _EMBEDDINGS)
    (DATA_DIR / "yc_embed_meta.json").write_text(
        json.dumps({"backend": _EMBEDDING_BACKEND, "count": len(companies)}),
        encoding="utf-8",
    )


def _embed_query(query: str) -> np.ndarray:
    _ensure_embeddings()
    assert _EMBEDDINGS is not None

    if _EMBEDDING_BACKEND == "sentence-transformers":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        vec = model.encode([query], show_progress_bar=False)[0]
        return np.asarray(vec, dtype=np.float32)

    assert _VECTORIZER is not None
    return _VECTORIZER.transform([query]).toarray()[0].astype(np.float32)


def _cosine_top_k(query_vec: np.ndarray, matrix: np.ndarray, k: int) -> list[int]:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    scores = m @ q
    k = min(k, len(scores))
    return np.argsort(scores)[-k:][::-1].tolist()


def build_deck_query(deck: PitchDeck) -> str:
    return " ".join(
        [
            deck.problem,
            deck.customer,
            deck.solution,
            deck.wedge,
        ]
    )


def format_precedents_block(matches: list[dict[str, str]]) -> str:
    if not matches:
        return ""
    lines = [
        f"- {m['name']} ({m['batch']}, {m['status']}) — {m['one_liner']}"
        for m in matches
    ]
    return "<precedents>\n" + "\n".join(lines) + "\n</precedents>\n\n"


@weave.op
async def retrieve_yc_precedents(deck: PitchDeck, k: int = TOP_K) -> list[dict[str, str]]:
    companies = _load_companies()
    _ensure_embeddings()
    assert _EMBEDDINGS is not None

    query = build_deck_query(deck)
    qvec = _embed_query(query)
    indices = _cosine_top_k(qvec, _EMBEDDINGS, k)
    return [companies[i] for i in indices]
