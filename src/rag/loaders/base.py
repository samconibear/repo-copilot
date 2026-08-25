from typing import Iterable, Protocol, runtime_checkable

from .models import SourceFile


@runtime_checkable
class Loader(Protocol):
    def load(self) -> Iterable[SourceFile]:
        pass
