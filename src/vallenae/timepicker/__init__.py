"""
Timerpicker
===========

The determination of signal arrival times has a major influence on the localization accuracy.
Usually, arrival times are determined by the first threshold crossing (either fixed or adaptive).
Following popular methods have been proposed in the past to automatically pick time of arrivals:

.. autosummary::
    :toctree: generated

    hinkley
    aic
    energy_ratio
    modified_energy_ratio
"""

import math
from typing import Tuple

import numpy as np

from .._numba import USE_NUMBA, njit


def _hinkley_numpy(arr: np.ndarray, alpha: int = 5) -> Tuple[np.ndarray, int]:
    n = len(arr)
    energy_cum = np.cumsum(arr ** 2, dtype=np.float64)
    negative_trend = energy_cum[-1] / (alpha * n)
    result = energy_cum - (np.arange(n, dtype=np.float32) * negative_trend)
    return result, np.argmin(result)


@njit
def _hinkley_numba(arr: np.ndarray, alpha: int = 5) -> Tuple[np.ndarray, int]:
    n = len(arr)
    result = np.zeros(n, dtype=np.float32)

    total_energy = 0.0
    for i in range(n):
        total_energy += arr[i] ** 2

    negative_trend = total_energy / (alpha * n)

    min_value = math.inf
    min_index = 0

    partial_energy = 0.0
    for i in range(n):
        partial_energy += arr[i] ** 2
        result[i] = partial_energy - (i * negative_trend)
        if result[i] < min_value:
            min_value = result[i]
            min_index = i

    return result, min_index


def hinkley(arr: np.ndarray, alpha: int = 5) -> Tuple[np.ndarray, int]:
    """
    Hinkley criterion for arrival time estimation.

    The Hinkley criterion is defined as the partial energy of the signal
    (cumulative square sum) with an applied negative trend (characterized by alpha).

    The starting value of alpha is reduced iteratively to avoid wrong picks within the
    pre-trigger part of the signal.
    Usually alpha values are chosen to be between 2 and 200 to ensure minimal delay.
    The chosen alpha value for the Hinkley criterion influences the results significantly.

    Args:
        arr: Transient signal of hit
        alpha: Divisor of the negative trend. Default: 5

    Returns:
        - Array with computed detection function
        - Index of the estimated arrival time (max value)

    References:
        - Molenda, M. (2016). Acoustic Emission monitoring of
          laboratory hydraulic fracturing experiments. Ruhr-Universität Bochum.
        - van Rijn, N. (2017).
          Investigating the Behaviour of Acoustic Emission Waves Near Cracks:
          Using the Finite Element Method. Delft University of Technology.
    """
    if USE_NUMBA:
        return _hinkley_numba(arr, alpha)
    return _hinkley_numpy(arr, alpha)


@njit
def _aic_numba(arr: np.ndarray) -> Tuple[np.ndarray, int]:
    n = len(arr)
    result = np.full(n, np.nan, dtype=np.float32)
    safety_eps = np.finfo(np.float32).tiny

    min_value = math.inf
    min_index = 0

    l_sum = 0.0
    r_sum = 0.0
    l_squaresum = 0.0
    r_squaresum = 0.0

    for i in range(n):
        r_sum += arr[i]
        r_squaresum += arr[i] ** 2

    for i in range(n - 1):
        l_sum += arr[i]
        l_squaresum += arr[i] ** 2

        r_sum -= arr[i]
        r_squaresum -= arr[i] ** 2

        l_len = i + 1
        r_len = n - i - 1

        l_variance = (1 / l_len) * l_squaresum - ((1 / l_len) * l_sum) ** 2
        r_variance = (1 / r_len) * r_squaresum - ((1 / r_len) * r_sum) ** 2

        # catch negative and very small values < safety_eps
        l_variance = max(l_variance, safety_eps)
        r_variance = max(r_variance, safety_eps)

        result[i] = (
            (i + 1) * math.log(l_variance) / math.log(10) +
            (n - i - 2) * math.log(r_variance) / math.log(10)
        )

        if result[i] < min_value:
            min_value = result[i]
            min_index = i

    return result, min_index


def _aic_numpy(arr: np.ndarray) -> Tuple[np.ndarray, int]:
    n = len(arr)
    safety_eps = np.finfo(np.float32).tiny

    l_sum = np.cumsum(arr, dtype=np.float64)
    l_squaresum = np.cumsum(arr ** 2, dtype=np.float64)
    r_sum = l_sum[-1] - l_sum
    r_squaresum = l_squaresum[-1] - l_squaresum

    index = np.arange(n)
    l_len = index + 1
    r_len = n - index - 1

    with np.errstate(divide="ignore", invalid="ignore"):
        l_variance = (1 / l_len) * l_squaresum - ((1 / l_len) * l_sum) ** 2
        r_variance = (1 / r_len) * r_squaresum - ((1 / r_len) * r_sum) ** 2

    # catch negative and very small values < safety_eps
    np.maximum(l_variance, safety_eps, out=l_variance)
    np.maximum(r_variance, safety_eps, out=r_variance)

    result = (index + 1) * np.log10(l_variance) + (n - index - 2) * np.log10(r_variance)
    return result, np.nanargmin(result)


@njit
def aic(arr: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    Akaike Information Criterion (AIC) for arrival time estimation.

    The AIC picker basically models the signal as an autoregressive (AR) process.
    A typical AE signal can be subdivided into two parts.
    The first part containing noise and the second part containing noise and the AE signal.
    Both parts of the signal contain non deterministic parts (noise) describable by a
    Gaussian distribution.

    Args:
        arr: Transient signal of hit

    Returns:
        - Array with computed detection function
        - Index of the estimated arrival time (max value)

    References:
        - Molenda, M. (2016). Acoustic Emission monitoring
          of laboratory hydraulic fracturing experiments.
          Ruhr-Universität Bochum.
        - Bai, F., Gagar, D., Foote, P., & Zhao, Y. (2017).
          Comparison of alternatives to amplitude thresholding for onset detection
          of acoustic emission signals.
          Mechanical Systems and Signal Processing, 84, 717-730.
        - van Rijn, N. (2017).
          Investigating the Behaviour of Acoustic Emission Waves Near Cracks:
          Using the Finite Element Method. Delft University of Technology.
    """
    if USE_NUMBA:
        return _aic_numba(arr)
    return _aic_numpy(arr)


@njit
def _energy_ratio_numba(arr: np.ndarray, win_len: int = 100) -> Tuple[np.ndarray, int]:
    n = len(arr)
    result = np.zeros(n, dtype=np.float32)

    max_value = -math.inf
    max_index = 0

    l_squaresum = 0.0
    r_squaresum = 0.0

    for i in range(0, win_len):
        l_squaresum += arr[i] ** 2

    for i in range(win_len, win_len + win_len):
        r_squaresum += arr[i] ** 2

    for i in range(win_len, n - win_len):
        l_squaresum += arr[i] ** 2
        r_squaresum += arr[i + win_len] ** 2
        l_squaresum -= arr[i - win_len] ** 2
        r_squaresum -= arr[i] ** 2
        result[i] = r_squaresum / l_squaresum
        if result[i] > max_value:
            max_value = result[i]
            max_index = i

    return result, max_index


def _energy_ratio_numpy(arr: np.ndarray, win_len: int = 100) -> Tuple[np.ndarray, int]:
    squaresum_cum = np.cumsum(arr ** 2, dtype=np.float64)

    l_squaresum = squaresum_cum[win_len:-win_len] - squaresum_cum[0:-2 * win_len]
    r_squaresum = squaresum_cum[2 * win_len:] - squaresum_cum[win_len:-win_len]

    result = np.zeros_like(arr, dtype=np.float32)
    result[win_len:-win_len] = r_squaresum / l_squaresum
    return result, np.argmax(result)


def energy_ratio(arr: np.ndarray, win_len: int = 100) -> Tuple[np.ndarray, int]:
    """
    Energy ratio for arrival time estimation.

    Method based on preceding and following energy collection windows.

    Args:
        arr: Transient signal of hit
        win_len: Samples of sliding windows. Default: 100

    Returns:
        - Array with computed detection function
        - Index of the estimated arrival time (max value)

    References:
        - Han, L., Wong, J., & Bancroft, J. C. (2009).
          Time picking and random noise reduction on microseismic data.
          CREWES Research Report, 21, 1-13.
    """
    if USE_NUMBA:
        return _energy_ratio_numba(arr, win_len)
    return _energy_ratio_numpy(arr, win_len)


def modified_energy_ratio(arr: np.ndarray, win_len: int = 100) -> Tuple[np.ndarray, int]:
    """
    Modified energy ratio method for arrival time estimation.

    The modifications improve the ability to detect the onset of a seismic
    arrival in the presence of random noise.

    Args:
        arr: Transient signal of hit
        win_len: Samples of sliding windows. Default: 100

    Returns:
        - Array with computed detection function
        - Index of the estimated arrival time (max value)

    References:
        - Han, L., Wong, J., & Bancroft, J. C. (2009).
          Time picking and random noise reduction on microseismic data.
          CREWES Research Report, 21, 1-13.
    """
    result, _ = energy_ratio(arr, win_len)
    np.multiply(result, np.abs(arr), out=result)
    # faster than np.power(result, 3, out=result)
    np.multiply(result, result, out=result)
    np.multiply(result, result, out=result)
    return result, np.argmax(result)
