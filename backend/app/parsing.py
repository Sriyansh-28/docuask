"""Text extraction and chunking for uploaded documents (Session 2).

Kept intentionally lightweight — the product value is in the upload UX and
error handling, not in sophisticated parsing. Raw text is used as-is; PDFs are
run through pypdf. Anything we cannot turn into usable text raises
``DocumentError`` with a message safe to show the user.
"""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentError(Exception):
    """A user-facing parse failure.

    The message is written to be shown directly in the UI, so it must not leak
    stack traces or internal detail.
    """


def extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes, raising ``DocumentError`` on any failure.

    Handles the failure modes called out in the spec: unreadable/broken files,
    password-protected files, and PDFs with no selectable text (e.g. scans).
    """
    try:
        reader = PdfReader(io.BytesIO(data))
    except (PdfReadError, OSError, ValueError) as exc:
        raise DocumentError("This file could not be read as a PDF.") from exc

    if reader.is_encrypted:
        # Try an empty password first (common for owner-only protection).
        # pypdf returns 0 when the password does not unlock the file.
        try:
            unlocked = reader.decrypt("") != 0
        except (NotImplementedError, PdfReadError):
            unlocked = False
        if not unlocked:
            raise DocumentError(
                "This PDF is password-protected. Remove the password and try again."
            )

    try:
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError) as exc:
        raise DocumentError("The text of this PDF could not be extracted.") from exc

    text = "\n".join(pages).strip()
    if not text:
        raise DocumentError(
            "No selectable text was found in this PDF. It may be a scanned image."
        )
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split text into overlapping character windows.

    Whitespace is normalised first so chunks are compact. Overlap keeps context
    from being cut mid-thought at chunk boundaries. Returns ``[]`` for empty
    input.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    normalised = " ".join(text.split())
    if not normalised:
        return []

    chunks: list[str] = []
    start = 0
    n = len(normalised)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(normalised[start:end])
        if end == n:
            break
        start = end - overlap
    return chunks
