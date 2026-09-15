"""Interactive AI Diff Reviewer and Chunk Acceptance Engine (Milestone E).

Allows authors to review AI suggestions chunk-by-chunk, accept all,
reject all, or accept individual segments before committing to formal text.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class DiffChunkStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class DiffChunkType(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


@dataclass
class DiffChunk:
    chunk_id: str
    chunk_type: DiffChunkType
    original_text: str
    suggested_text: str
    status: DiffChunkStatus = DiffChunkStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "type": self.chunk_type.value,
            "original_text": self.original_text,
            "suggested_text": self.suggested_text,
            "status": self.status.value,
        }


class DiffReviewSession:
    """Manages an interactive diff review session for a document modification."""

    def __init__(self, original_text: str, suggested_text: str) -> None:
        self.original_text = original_text or ""
        self.suggested_text = suggested_text or ""
        self.chunks: List[DiffChunk] = []
        self._build_chunks()

    def _build_chunks(self) -> None:
        matcher = difflib.SequenceMatcher(None, self.original_text, self.suggested_text)
        chunk_idx = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            orig_sub = self.original_text[i1:i2]
            sugg_sub = self.suggested_text[j1:j2]

            if tag == "equal":
                self.chunks.append(
                    DiffChunk(
                        chunk_id=f"chk_{chunk_idx}",
                        chunk_type=DiffChunkType.EQUAL,
                        original_text=orig_sub,
                        suggested_text=sugg_sub,
                        status=DiffChunkStatus.ACCEPTED,
                    )
                )
            elif tag == "insert":
                self.chunks.append(
                    DiffChunk(
                        chunk_id=f"chk_{chunk_idx}",
                        chunk_type=DiffChunkType.INSERT,
                        original_text="",
                        suggested_text=sugg_sub,
                        status=DiffChunkStatus.PENDING,
                    )
                )
            elif tag == "delete":
                self.chunks.append(
                    DiffChunk(
                        chunk_id=f"chk_{chunk_idx}",
                        chunk_type=DiffChunkType.DELETE,
                        original_text=orig_sub,
                        suggested_text="",
                        status=DiffChunkStatus.PENDING,
                    )
                )
            elif tag == "replace":
                self.chunks.append(
                    DiffChunk(
                        chunk_id=f"chk_{chunk_idx}",
                        chunk_type=DiffChunkType.REPLACE,
                        original_text=orig_sub,
                        suggested_text=sugg_sub,
                        status=DiffChunkStatus.PENDING,
                    )
                )
            chunk_idx += 1

    def list_chunks(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.chunks]

    def accept_chunk(self, chunk_id: str) -> bool:
        for c in self.chunks:
            if c.chunk_id == chunk_id and c.chunk_type != DiffChunkType.EQUAL:
                c.status = DiffChunkStatus.ACCEPTED
                return True
        return False

    def reject_chunk(self, chunk_id: str) -> bool:
        for c in self.chunks:
            if c.chunk_id == chunk_id and c.chunk_type != DiffChunkType.EQUAL:
                c.status = DiffChunkStatus.REJECTED
                return True
        return False

    def accept_all(self) -> None:
        for c in self.chunks:
            if c.chunk_type != DiffChunkType.EQUAL:
                c.status = DiffChunkStatus.ACCEPTED

    def reject_all(self) -> None:
        for c in self.chunks:
            if c.chunk_type != DiffChunkType.EQUAL:
                c.status = DiffChunkStatus.REJECTED

    def render_result(self) -> str:
        """Compute the final merged text based on user decisions."""
        parts = []
        for c in self.chunks:
            if c.chunk_type == DiffChunkType.EQUAL:
                parts.append(c.original_text)
            elif c.status == DiffChunkStatus.ACCEPTED:
                # Accepted: apply AI suggestion
                parts.append(c.suggested_text)
            else:
                # Rejected or Pending: keep original text
                parts.append(c.original_text)
        return "".join(parts)
