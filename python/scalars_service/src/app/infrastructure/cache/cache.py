from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):

    @abstractmethod
    async def get(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    async def remove(self, key: str) -> None:
        pass

    @abstractmethod
    async def invalidate(self, pattern: str) -> None:
        pass
