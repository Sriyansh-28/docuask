"""In-memory document store (Session 2).

A single process-local index keyed by document id. This is deliberately not a
database — persistence of interactions/telemetry comes later (Session 4). The
store holds the extracted chunks so the retrieval loop (Session 3) can build an
index over them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Document:
    """A parsed, chunked document ready for retrieval."""

    id: str
    chunks: list[str]
    num_chars: int
    filename: str | None = None

    @property
    def num_chunks(self) -> int:
        return len(self.chunks)


@dataclass
class DocumentStore:
    """Process-local map of document id → :class:`Document`."""

    _docs: dict[str, Document] = field(default_factory=dict)

    def add(self, chunks: list[str], num_chars: int, filename: str | None = None) -> Document:
        doc_id = uuid4().hex[:12]
        doc = Document(id=doc_id, chunks=chunks, num_chars=num_chars, filename=filename)
        self._docs[doc_id] = doc
        return doc

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def __contains__(self, doc_id: str) -> bool:
        return doc_id in self._docs

    def __len__(self) -> int:
        return len(self._docs)


# A module-level singleton is fine for the in-memory skeleton.
store = DocumentStore()
