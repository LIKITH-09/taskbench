import pytest

from taskbench.retrieval import BM25Index, format_passages, tokenize
from taskbench.schema import Passage


def p(pid: str, text: str, heading: str = "h") -> Passage:
    return Passage(id=pid, source_path="x", heading=heading, text=text, license="MIT")


CORPUS = [
    p("P0001", "Set INSPECT_LOG_DIR to change the log directory."),
    p("P0002", "The fail_on_error option tolerates sample errors."),
    p("P0003", "Caching stores model responses."),
    p("P0004", "Sandboxes run untrusted code in Docker."),
]


def test_tokenize_splits_snake_case():
    assert tokenize("fail_on_error!") == ["fail_on_error", "fail", "on", "error"]
    assert tokenize("   ") == []


def test_search_finds_relevant_passage():
    hits = BM25Index(CORPUS).search("which option tolerates errors", k=2)
    assert hits[0].passage.id == "P0002"


def test_search_is_deterministic():
    idx = BM25Index(CORPUS)
    assert [h.passage.id for h in idx.search("log directory", 3)] == [
        h.passage.id for h in idx.search("log directory", 3)
    ]


def test_k_bounds_and_empty_query():
    idx = BM25Index(CORPUS)
    assert len(idx.search("errors log caching docker", k=2)) <= 2
    assert idx.search("!!!", k=3) == []
    with pytest.raises(ValueError):
        idx.search("x", k=0)


def test_index_rejects_bad_corpus():
    with pytest.raises(ValueError):
        BM25Index([])
    with pytest.raises(ValueError, match="unique"):
        BM25Index([CORPUS[0], CORPUS[0]])


def test_format_passages_labels_ids():
    text = format_passages(BM25Index(CORPUS).search("log directory", 1))
    assert text.startswith("[P0001]")
