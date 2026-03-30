from pydantic import BaseModel


class UploadBlobResult(BaseModel):
    """Result of a blob upload."""

    size: int
    hash: str
