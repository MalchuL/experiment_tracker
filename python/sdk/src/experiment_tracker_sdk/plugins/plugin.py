from abc import ABC, abstractmethod


class Plugin(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def version(self) -> str:
        pass
