"""Text normalization, tokenization, and chunking for keyword retrieval."""

from collections import Counter
import re

MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.'-]*")
_HORIZONTAL_WHITESPACE = re.compile(r"[ \t]+")

STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "of", "on", "or", "our", "that",
    "the", "their", "this", "to", "with", "you", "your",
})


def clean_text(text: str) -> str:
    """Collapse whitespace inside paragraphs and separate paragraphs with one blank line."""
    lines = [
        _HORIZONTAL_WHITESPACE.sub(" ", line).strip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return "\n\n".join(blocks)


def token_counts(text: str) -> Counter[str]:
    return Counter(
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if len(token) > 1 and token not in STOP_WORDS
    )


def chunk_text(text: str) -> list[str]:
    """Pack paragraphs into chunks of at most MAX_CHUNK_CHARS, overlapping between chunks."""
    text = clean_text(text)
    if not text:
        return []

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        for index, part in enumerate(_split_long_text(paragraph)):
            # Pieces of one paragraph are rejoined with a space; separate paragraphs keep their blank line.
            separator = " " if index > 0 else "\n\n"
            if not current:
                current = part
            elif len(current) + len(part) + len(separator) <= MAX_CHUNK_CHARS:
                current = f"{current}{separator}{part}"
            else:
                chunks.append(current)
                overlap = _tail_overlap(current)
                current = f"{overlap}{separator}{part}" if overlap else part

    if current:
        chunks.append(current)
    return chunks


def _tail_overlap(chunk: str) -> str:
    """The end of a chunk, repeated at the start of the next so text cut at the boundary keeps its context."""
    if len(chunk) <= CHUNK_OVERLAP_CHARS:
        return chunk.strip()
    tail = chunk[-CHUNK_OVERLAP_CHARS:]
    # Start at a word boundary, so the next chunk does not open with half a word.
    first_space = tail.find(" ")
    return tail[first_space + 1 :].strip() if first_space != -1 else tail.strip()


def _split_long_text(text: str) -> list[str]:
    """Split a single oversized paragraph on word boundaries.

    The parts do not overlap; ``chunk_text`` adds the overlap between chunks.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > MAX_CHUNK_CHARS:
        split_at = remaining.rfind(" ", 0, MAX_CHUNK_CHARS)
        if split_at < MAX_CHUNK_CHARS // 2:
            split_at = MAX_CHUNK_CHARS
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        parts.append(remaining)
    return parts
