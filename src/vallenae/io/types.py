from typing import TypeVar, Generic, Iterator
from typing_extensions import Protocol


T = TypeVar("T", covariant=True)
class SizedIterable(Protocol, Generic[T]):  # noqa: E302
    """Generic iterable, sized type that implements `__iter__` and `__len__`."""

    def __len__(self) -> int:
        ...

    def __iter__(self) -> Iterator[T]:
        ...
