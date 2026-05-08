"""Storage-layer value types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BlobListEntry(BaseModel):
    """One object in a bucket listing (full object key and size from the list API)."""

    model_config = ConfigDict(frozen=True)

    key: str
    size: int
