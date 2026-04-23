"""
embeddings.py — Semantic search engine for Shelf Bookstore.

Flow:
  1. On app startup, load the HuggingFace sentence-transformer model into memory.
  2. Build a FAISS index from all book embeddings stored in the DB
     (or load from disk if the .bin file already exists).
  3. On every semantic search query, encode the query → cosine-similarity
     search against the FAISS index → return ranked book_ids.
  4. Whenever a book synopsis changes (add / edit), re-embed and update the index.
"""

import os
import json
import logging
import numpy as np

from sentence_transformers import SentenceTransformer
import faiss

from config import Config
import models

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Module-level singletons (loaded once at startup)
# ──────────────────────────────────────────────────────────────
_model: SentenceTransformer | None = None
_index: faiss.IndexFlatIP | None = None   # Inner-Product = cosine after L2-norm
_index_book_ids: list[int] = []           # position i → book_id


# ══════════════════════════════════════════════════════════════
#  Model
# ══════════════════════════════════════════════════════════════

def load_model() -> SentenceTransformer:
    """Load the sentence-transformer model (downloads ~80 MB on first call)."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}")
        _model = SentenceTransformer(Config.EMBEDDING_MODEL)
        logger.info("Model loaded successfully.")
    return _model


def encode_text(text: str) -> np.ndarray:
    """
    Encode a single string to a unit-normalized 384-dim float32 vector.
    Unit normalisation allows inner-product to equal cosine similarity.
    """
    model = load_model()
    vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vec.astype(np.float32)


def encode_texts(texts: list[str]) -> np.ndarray:
    """Batch-encode a list of strings. Returns shape (N, 384) float32 array."""
    model = load_model()
    vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True,
                        batch_size=32, show_progress_bar=False)
    return vecs.astype(np.float32)


# ══════════════════════════════════════════════════════════════
#  FAISS Index
# ══════════════════════════════════════════════════════════════

def _build_index_from_db() -> tuple[faiss.IndexFlatIP, list[int]]:
    """
    Pull all embeddings from the DB and build a FAISS IndexFlatIP.
    Returns (index, book_ids_list).
    """
    rows = models.get_all_embeddings()     # [(book_id, vector_json), ...]
    if not rows:
        logger.warning("No embeddings found in DB. Index is empty.")
        idx = faiss.IndexFlatIP(Config.EMBEDDING_DIM)
        return idx, []

    book_ids = []
    vectors = []
    for book_id, vector_json in rows:
        try:
            vec = np.array(json.loads(vector_json), dtype=np.float32)
            if vec.shape[0] != Config.EMBEDDING_DIM:
                logger.warning(f"book_id={book_id} has wrong embedding dim {vec.shape[0]}, skipping.")
                continue
            book_ids.append(book_id)
            vectors.append(vec)
        except Exception as e:
            logger.error(f"Failed to parse embedding for book_id={book_id}: {e}")

    if not vectors:
        idx = faiss.IndexFlatIP(Config.EMBEDDING_DIM)
        return idx, []

    matrix = np.stack(vectors)   # (N, 384)
    idx = faiss.IndexFlatIP(Config.EMBEDDING_DIM)
    idx.add(matrix)
    logger.info(f"FAISS index built with {idx.ntotal} vectors.")
    return idx, book_ids


def load_index():
    """
    Load or build the FAISS index.
    - If a saved .bin file exists AND a book_ids .npy file exists → load from disk.
    - Otherwise → build from DB and save to disk.
    """
    global _index, _index_book_ids

    if os.path.exists(Config.FAISS_INDEX_PATH) and os.path.exists(Config.BOOK_IDS_PATH):
        try:
            _index = faiss.read_index(Config.FAISS_INDEX_PATH)
            _index_book_ids = np.load(Config.BOOK_IDS_PATH).tolist()
            logger.info(f"FAISS index loaded from disk ({_index.ntotal} vectors).")
            return
        except Exception as e:
            logger.error(f"Failed to load FAISS index from disk: {e}. Rebuilding...")

    _index, _index_book_ids = _build_index_from_db()
    _save_index()


def _save_index():
    """Persist FAISS index and book_id mapping to disk."""
    global _index, _index_book_ids
    if _index is None:
        return
    try:
        faiss.write_index(_index, Config.FAISS_INDEX_PATH)
        np.save(Config.BOOK_IDS_PATH, np.array(_index_book_ids, dtype=np.int32))
        logger.info("FAISS index saved to disk.")
    except Exception as e:
        logger.error(f"Failed to save FAISS index: {e}")


def rebuild_index():
    """
    Full rebuild: re-embed ALL book synopses from DB, save to Embeddings table,
    rebuild FAISS index and save to disk.
    Called by seed_books.py or via admin endpoint.
    """
    global _index, _index_book_ids

    rows = models.get_all_synopses_for_embedding()   # [(book_id, synopsis), ...]
    if not rows:
        logger.warning("No books found to embed.")
        return

    book_ids = [r[0] for r in rows]
    synopses = [r[1] for r in rows]

    logger.info(f"Encoding {len(synopses)} synopses...")
    vectors = encode_texts(synopses)   # (N, 384)

    # Save each vector to DB
    for book_id, vec in zip(book_ids, vectors):
        models.save_embedding(book_id, json.dumps(vec.tolist()))

    # Build FAISS
    _index = faiss.IndexFlatIP(Config.EMBEDDING_DIM)
    _index.add(vectors)
    _index_book_ids = book_ids
    _save_index()
    logger.info(f"Index rebuilt with {_index.ntotal} vectors.")


def add_book_to_index(book_id: int, synopsis: str):
    """
    Embed one synopsis and add it to the live FAISS index + DB.
    Called after a new book is added or a synopsis is edited.
    """
    global _index, _index_book_ids

    if _index is None:
        load_index()

    vec = encode_text(synopsis)   # (384,)
    models.save_embedding(book_id, json.dumps(vec.tolist()))

    # Remove old entry if present (FAISS FlatIP doesn't support deletion,
    # so we rebuild in place from DB for correctness)
    if book_id in _index_book_ids:
        _index, _index_book_ids = _build_index_from_db()
    else:
        _index.add(vec.reshape(1, -1))
        _index_book_ids.append(book_id)

    _save_index()
    logger.info(f"Book {book_id} added/updated in FAISS index.")


# ══════════════════════════════════════════════════════════════
#  Search
# ══════════════════════════════════════════════════════════════

def semantic_search(query: str, top_k: int = None) -> list[dict]:
    """
    Search for books semantically similar to `query`.

    Returns a list of dicts:
      [{'book_id': int, 'score': float}, ...]
    sorted by score descending, filtered by SIMILARITY_THRESHOLD.
    """
    global _index, _index_book_ids

    if top_k is None:
        top_k = Config.MAX_SEARCH_RESULTS

    if _index is None:
        load_index()

    if _index.ntotal == 0:
        return []

    query_vec = encode_text(query).reshape(1, -1)   # (1, 384)

    k = min(top_k, _index.ntotal)
    scores, indices = _index.search(query_vec, k)    # both shape (1, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:           # FAISS returns -1 for unfilled slots
            continue
        if score < Config.SIMILARITY_THRESHOLD:
            continue
        book_id = _index_book_ids[idx]
        results.append({'book_id': int(book_id), 'score': float(round(score, 4))})

    return results   # already sorted descending by FAISS


def more_like_this(book_id: int, top_k: int = 10) -> list[dict]:
    """
    Find books similar to a given book_id using its stored embedding.
    Excludes the book itself from results.
    """
    global _index, _index_book_ids

    if _index is None:
        load_index()

    if book_id not in _index_book_ids:
        return []

    pos = _index_book_ids.index(book_id)
    # Reconstruct the stored vector
    vec = _index.reconstruct(pos).reshape(1, -1)

    k = min(top_k + 1, _index.ntotal)   # +1 to exclude self
    scores, indices = _index.search(vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        similar_id = _index_book_ids[idx]
        if similar_id == book_id:        # exclude self
            continue
        if score < Config.SIMILARITY_THRESHOLD:
            continue
        results.append({'book_id': int(similar_id), 'score': float(round(score, 4))})

    return results[:top_k]
