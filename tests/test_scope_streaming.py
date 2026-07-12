import pytest

from deep_research_langgraph.scope.streaming import iter_text_chunks


def test_iter_text_chunks_preserves_text() -> None:
    text = "Streaming should keep words readable."

    assert "".join(iter_text_chunks(text, target_size=10)) == text


def test_iter_text_chunks_rejects_invalid_target_size() -> None:
    with pytest.raises(ValueError):
        list(iter_text_chunks("hello", target_size=0))
