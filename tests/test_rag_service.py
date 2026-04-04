# ══════════════════════════════════════════════════════════════════════════════
# tests/test_rag_service.py
# Tests for pure helper functions in rag_service — no ChromaDB needed
# ══════════════════════════════════════════════════════════════════════════════

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.rag_service import _chunk_text, _chunk_id, build_rag_context_block

# ── _chunk_text ───────────────────────────────────────────────────────────────
def test_chunk_short_text():
    text   = "Hello world this is a short text."
    chunks = _chunk_text(text, chunk_size=300)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_chunk_long_text():
    # 900 words → should produce multiple chunks of 300
    text   = " ".join([f"word{i}" for i in range(900)])
    chunks = _chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1

def test_chunk_overlap():
    # With overlap, second chunk should start before where first chunk ended
    text   = " ".join([f"w{i}" for i in range(600)])
    chunks = _chunk_text(text, chunk_size=300, overlap=100)
    # The first word of chunk 2 should appear in chunk 1
    first_word_c2 = chunks[1].split()[0]
    assert first_word_c2 in chunks[0]

def test_chunk_empty_text():
    chunks = _chunk_text("", chunk_size=300)
    # Should return at least one chunk (even if empty string)
    assert isinstance(chunks, list)

def test_chunk_preserves_content():
    text   = "Machine learning is a subset of artificial intelligence."
    chunks = _chunk_text(text, chunk_size=100)
    combined = " ".join(chunks)
    # All original words should be present
    for word in ["Machine", "learning", "artificial", "intelligence"]:
        assert word in combined

# ── _chunk_id ─────────────────────────────────────────────────────────────────
def test_chunk_id_deterministic():
    id1 = _chunk_id("user@test.com", "python", 0)
    id2 = _chunk_id("user@test.com", "python", 0)
    assert id1 == id2

def test_chunk_id_unique_per_index():
    id0 = _chunk_id("user@test.com", "python", 0)
    id1 = _chunk_id("user@test.com", "python", 1)
    assert id0 != id1

def test_chunk_id_unique_per_topic():
    id_py  = _chunk_id("user@test.com", "python", 0)
    id_sql = _chunk_id("user@test.com", "sql",    0)
    assert id_py != id_sql

def test_chunk_id_unique_per_user():
    id_u1 = _chunk_id("user1@test.com", "python", 0)
    id_u2 = _chunk_id("user2@test.com", "python", 0)
    assert id_u1 != id_u2

def test_chunk_id_is_string():
    cid = _chunk_id("a@b.com", "topic", 5)
    assert isinstance(cid, str)
    assert len(cid) > 0

# ── build_rag_context_block ───────────────────────────────────────────────────
def test_build_context_empty():
    result = build_rag_context_block([])
    assert result == ""

def test_build_context_single_chunk():
    chunks = [("Gradient descent minimises loss.", "machine learning", 0.92)]
    result = build_rag_context_block(chunks)
    assert "Gradient descent" in result
    assert "Machine Learning" in result or "machine learning" in result.lower()
    assert "92%" in result

def test_build_context_multiple_chunks():
    chunks = [
        ("Python is a programming language.", "python", 0.95),
        ("It supports OOP and functional styles.", "python", 0.88),
    ]
    result = build_rag_context_block(chunks)
    assert "Note 1" in result
    assert "Note 2" in result

def test_build_context_has_instruction():
    chunks = [("Some content here.", "topic", 0.80)]
    result = build_rag_context_block(chunks)
    # Should include the grounding instruction for the LLM
    assert "reference" in result.lower() or "relevant" in result.lower()
