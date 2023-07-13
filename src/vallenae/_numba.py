"""Optional usage of numba with njit decorator."""

import warnings

USE_NUMBA = True

try:
    from numba import njit
except ImportError:
    USE_NUMBA = False

    # https://stackoverflow.com/a/73275170/9967707
    def njit(f=None, *args, **kwargs):
        if callable(f):
            return f
        return lambda func: func


class PerformanceWarning(Warning):
    """Warning raised when there is a possible performance impact."""


if not USE_NUMBA:
    warnings.warn(
        "Numba not found. Use Numba (pip install numba) for better performance.",
        PerformanceWarning,
        stacklevel=1,
    )
