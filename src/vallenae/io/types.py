from typing import Generic, Iterator, TypeVar

from typing_extensions import Protocol

T_co = TypeVar("T_co", covariant=True)
class SizedIterable(Protocol, Generic[T_co]):
    """Generic iterable, sized type that implements `__iter__` and `__len__`."""

    def __len__(self) -> int:  # pragma: no cover
        return 0

    def __iter__(self) -> Iterator[T_co]:  # pragma: no cover
        return iter([])
