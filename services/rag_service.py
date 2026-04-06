# ══════════════════════════════════════════════════════════════════════════════
# services/rag_service.py — RAG (Retrieval-Augmented Generation) Engine
#
# THE WOW FEATURE — "Chat With Your Own Notes"
#
# How it works:
#   1. Every note the user saves is chunked into ~300-word segments
#   2. Each chunk is embedded using a lightweight sentence-transformers model
#   3. Embeddings are stored in a per-user ChromaDB collection
#   4. When the AI Tutor answers a question, the top-3 relevant note chunks
#      are retrieved and injected as grounding context into the prompt
#   5. The LLM answers using the student's own notes — not generic knowledge
#
# Result: The tutor says "Based on your notes on Gradient Descent from 3 days
# ago, you described it as..." — which feels genuinely personalised.
#
# Dependencies (all lightweight, no GPU needed):
#   chromadb>=0.5.0
#   sentence-transformers>=3.0.0
#
# Graceful degradation:
#   If either library is missing, RAG silently falls back to standard tutor.
#   The app never crashes — RAG is an enhancement, not a hard dependency.
# ══════════════════════════════════════════════════════════════════════════════

import os
import re
import hashlib
from typing import List, Optional, Tuple

# ── Optional imports with graceful degradation ────────────────────────────────
# Uses broad Exception catch because chromadb can crash at C-level (protobuf
# conflict) which bypasses ImportError on some platforms (Streamlit Cloud).
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except Exception:
    ST_AVAILABLE = False

RAG_AVAILABLE = CHROMA_AVAILABLE and ST_AVAILABLE

# ── Module-level singletons (lazy-initialised) ────────────────────────────────
_embed_model: Optional[object] = None
_chroma_client: Optional[object] = None

# ChromaDB persistence directory — stored alongside the app
_CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", ".chroma_db")

# Embedding model — small, fast, CPU-friendly (22MB)
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Chunking parameters
_CHUNK_SIZE     = 300   # words per chunk
_CHUNK_OVERLAP  = 50    # words of overlap between consecutive chunks
_TOP_K          = 3     # number of chunks to retrieve per query


def _get_embed_model():
    """Lazily load the sentence-transformer embedding model."""
    global _embed_model
    if _embed_model is None and ST_AVAILABLE:
        try:
            _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
        except Exception:
            _embed_model = None
    return _embed_model


def _get_chroma_client():
    """Lazily initialise a persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None and CHROMA_AVAILABLE:
        try:
            os.makedirs(_CHROMA_DIR, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(
                path=_CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception:
            _chroma_client = None
    return _chroma_client


def _collection_name(email: str) -> str:
    """
    Derive a safe ChromaDB collection name from a user email.
    ChromaDB requires names to be 3-63 chars, alphanumeric + hyphens only.
    """
    safe = re.sub(r"[^a-zA-Z0-9]", "-", email)[:50]
    # Ensure minimum length and valid start character
    return f"u-{safe}" if safe else "u-default"


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def is_available() -> bool:
    """Return True if both chromadb and sentence-transformers are installed."""
    return RAG_AVAILABLE


def index_note(email: str, topic: str, notes_text: str) -> bool:
    """
    Chunk a note and upsert all chunks into the user's ChromaDB collection.

    Called automatically from pages/notes.py whenever a note is saved.
    Safe to call multiple times for the same topic (upsert semantics).

    Returns True on success, False on any failure.
    """
    if not RAG_AVAILABLE:
        return False

    model  = _get_embed_model()
    client = _get_chroma_client()
    if not model or not client:
        return False

    try:
        collection = client.get_or_create_collection(
            name=_collection_name(email),
            metadata={"hnsw:space": "cosine"},
        )

        chunks     = _chunk_text(notes_text)
        ids        = [_chunk_id(email, topic, i) for i in range(len(chunks))]
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()
        metadatas  = [{"topic": topic, "chunk_index": i} for i in range(len(chunks))]

        # Upsert: safe to re-index the same topic after regeneration
        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return True

    except Exception:
        return False


def retrieve_context(email: str, query: str, top_k: int = _TOP_K) -> List[Tuple[str, str, float]]:
    """
    Retrieve the most relevant note chunks for a given query.

    Returns a list of (chunk_text, topic, relevance_score) tuples,
    ordered by relevance descending. Returns [] on any failure.
    """
    if not RAG_AVAILABLE:
        return []

    model  = _get_embed_model()
    client = _get_chroma_client()
    if not model or not client:
        return []

    try:
        collection = client.get_collection(name=_collection_name(email))
        query_embedding = model.encode([query], show_progress_bar=False).tolist()[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert cosine distance (0=identical, 2=opposite) to similarity score (0-1)
            relevance = round(1 - dist / 2, 3)
            chunks.append((doc, meta.get("topic", ""), relevance))

        return chunks

    except Exception:
        # Collection may not exist yet (user has no notes indexed)
        return []


def build_rag_context_block(chunks: List[Tuple[str, str, float]]) -> str:
    """
    Format retrieved chunks into a prompt context block.

    The block is injected into the tutor prompt before the user's question
    so the LLM grounds its answer in the student's actual notes.
    """
    if not chunks:
        return ""

    lines = ["📚 CONTEXT FROM YOUR OWN NOTES (use this to personalise your answer):"]
    for i, (text, topic, score) in enumerate(chunks, 1):
        lines.append(f"\n[Note {i} — Topic: {topic.title()} | Relevance: {score:.0%}]")
        lines.append(text.strip())

    lines.append(
        "\n(If the above notes are relevant to the question, reference them specifically "
        "in your answer — e.g. 'As you noted about {topic}...')"
    )
    return "\n".join(lines)


def delete_user_index(email: str) -> bool:
    """Delete a user's entire ChromaDB collection. Used on logout/account reset."""
    if not RAG_AVAILABLE:
        return False

    client = _get_chroma_client()
    if not client:
        return False

    try:
        client.delete_collection(name=_collection_name(email))
        return True
    except Exception:
        return False


def get_indexed_topics(email: str) -> List[str]:
    """Return list of distinct topics indexed for this user."""
    if not RAG_AVAILABLE:
        return []

    client = _get_chroma_client()
    if not client:
        return []

    try:
        collection = client.get_collection(name=_collection_name(email))
        results = collection.get(include=["metadatas"])
        topics = list({m.get("topic", "") for m in results["metadatas"]})
        return sorted(t for t in topics if t)
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping word-count chunks.

    Overlapping chunks ensure that sentences spanning a chunk boundary
    are still captured in at least one chunk's context window.
    """
    words  = text.split()
    chunks = []
    step   = chunk_size - overlap
    i      = 0

    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += step

    # Always return at least one chunk even for very short notes
    return chunks if chunks else [text]


def _chunk_id(email: str, topic: str, index: int) -> str:
    """
    Generate a stable, unique ID for a chunk.
    Stable = same email+topic+index always produces the same ID (enables upsert).
    """
    raw = f"{email}::{topic}::{index}"
    return hashlib.md5(raw.encode()).hexdigest()
