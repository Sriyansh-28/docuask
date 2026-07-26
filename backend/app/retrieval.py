"""Hybrid retrieval for the chat loop (Session 3).

Per the project spec the retrieval is intentionally lightweight: a single
in-memory index per document combining lexical **BM25** with a **FAISS** cosine
search over TF-IDF vectors. There is no generation model in the stack, so the
"answer" is extractive — the sentence in the top passage that best overlaps the
question.

The two signals are min-max normalised across the document's chunks and
averaged, which keeps a keyword hit (BM25) and a fuzzy/semantic-ish match
(TF-IDF/FAISS) both able to surface the right passage.
"""

from __future__ import annotations

import re

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _minmax(scores: np.ndarray) -> np.ndarray:
    """Scale to [0, 1]; return zeros when every score is equal (no signal)."""
    lo = float(scores.min())
    hi = float(scores.max())
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def best_sentence(passage: str, question: str) -> str:
    """Return the sentence in ``passage`` with the most question-term overlap."""
    q_terms = set(_tokenize(question))
    best = passage.strip()
    best_score = -1
    for sentence in _SENTENCE_RE.split(passage):
        overlap = len(q_terms & set(_tokenize(sentence)))
        if overlap > best_score:
            best_score = overlap
            best = sentence.strip()
    return best


class DocumentIndex:
    """BM25 + TF-IDF/FAISS index over a single document's chunks."""

    def __init__(self, chunks: list[str]) -> None:
        if not chunks:
            raise ValueError("cannot index an empty document")
        self.chunks = chunks

        self._bm25 = BM25Okapi([_tokenize(c) for c in chunks])

        self._vectorizer = TfidfVectorizer()
        dense = self._vectorizer.fit_transform(chunks).toarray().astype("float32")
        faiss.normalize_L2(dense)
        self._faiss = faiss.IndexFlatIP(dense.shape[1])
        self._faiss.add(dense)

    def _cosine_scores(self, query: str) -> np.ndarray:
        """Cosine similarity of the query against every chunk (0 if no terms)."""
        n = len(self.chunks)
        scores = np.zeros(n, dtype="float32")
        vec = self._vectorizer.transform([query]).toarray().astype("float32")
        if float(np.linalg.norm(vec)) == 0.0:
            return scores  # no overlapping vocabulary
        faiss.normalize_L2(vec)
        sims, idx = self._faiss.search(vec, n)
        scores[idx[0]] = sims[0]
        return scores

    def search(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        """Return up to ``k`` ``(chunk_index, combined_score)`` pairs, best first."""
        bm25 = np.asarray(self._bm25.get_scores(_tokenize(query)), dtype="float32")
        cosine = self._cosine_scores(query)
        combined = 0.5 * _minmax(bm25) + 0.5 * _minmax(cosine)

        k = min(k, len(self.chunks))
        top = np.argsort(-combined)[:k]
        return [(int(i), float(combined[i])) for i in top]
