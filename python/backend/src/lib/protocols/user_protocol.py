from typing import Protocol
from uuid import UUID


class UserProtocol(Protocol):
    @property
    def id(self) -> UUID | str:
        pass
