from typing import Generic, Iterator, TypeVar

from typing_extensions import Protocol

T = TypeVar("T", covariant=True)
class SizedIterable(Protocol, Generic[T]):  # noqa: E302
    """Generic iterable, sized type that implements `__iter__` and `__len__`."""

    def __len__(self) -> int:  # pragma: no cover
        return 0

    def __iter__(self) -> Iterator[T]:  # pragma: no cover
        return iter([])
