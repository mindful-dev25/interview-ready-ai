import asyncio

from app.storage.vector_store import VectorStore
from app.storage.vector_store.text import CHUNK_OVERLAP_CHARS, MAX_CHUNK_CHARS

DOCUMENTS = [
    {"content": "Built Python APIs with FastAPI and PostgreSQL.", "source_type": "resume", "source": "Resume"},
    {"content": "The company values teamwork and curiosity.", "source_type": "company_research", "source": "Acme"},
]


def test_search_ranks_the_matching_document_first(tmp_path):
    store = VectorStore(persist_dir=str(tmp_path))
    asyncio.run(store.replace_documents("session", DOCUMENTS))

    results = asyncio.run(store.similarity_search("session", "python fastapi experience", limit=1))

    assert len(results) == 1
    assert results[0]["source_type"] == "resume"
    assert results[0]["id"].startswith("evidence-")
    assert "python" in results[0]["relevance"]


def test_search_sees_documents_written_after_an_earlier_search(tmp_path):
    store = VectorStore(persist_dir=str(tmp_path))
    asyncio.run(store.replace_documents("session", DOCUMENTS))
    asyncio.run(store.similarity_search("session", "python"))

    asyncio.run(store.replace_documents("session", ["Notes about gardening and tomatoes."]))
    results = asyncio.run(store.similarity_search("session", "gardening"))

    assert [result["quote"] for result in results] == ["Notes about gardening and tomatoes."]


def test_add_documents_does_not_duplicate_existing_chunks(tmp_path):
    store = VectorStore(persist_dir=str(tmp_path))
    asyncio.run(store.add_documents("session", DOCUMENTS))
    asyncio.run(store.add_documents("session", DOCUMENTS))

    assert len(asyncio.run(store.similarity_search("session", "anything", limit=10))) == 2


def test_search_on_unknown_collection_is_empty(tmp_path):
    store = VectorStore(persist_dir=str(tmp_path))

    assert asyncio.run(store.similarity_search("missing", "python")) == []


def test_long_text_is_split_into_overlapping_chunks(tmp_path):
    store = VectorStore(persist_dir=str(tmp_path))
    asyncio.run(store.replace_documents("session", ["word " * 600]))

    results = asyncio.run(store.similarity_search("session", "word", limit=10))

    # A chunk may exceed the limit by the overlap carried over from the previous chunk.
    longest_allowed = MAX_CHUNK_CHARS + CHUNK_OVERLAP_CHARS + len("\n\n")
    assert len(results) > 1
    assert all(len(result["quote"]) <= longest_allowed for result in results)
