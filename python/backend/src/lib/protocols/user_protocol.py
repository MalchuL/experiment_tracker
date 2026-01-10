from typing import Protocol
from uuid import UUID


class UserProtocol(Protocol):
    id: UUID | str
