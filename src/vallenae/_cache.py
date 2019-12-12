from functools import lru_cache
from typing import TypeVar, Callable


T = TypeVar('T')
def cache(*args, **kwargs):  # noqa: E302
    def wrapper(func: Callable[..., T]) -> T:
        return lru_cache(*args, **kwargs)(func)  # type: ignore
    return wrapper
