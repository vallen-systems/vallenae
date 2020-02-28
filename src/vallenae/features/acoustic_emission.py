import math
from typing import Optional

import numpy as np
from numba import njit


@njit
def peak_amplitude(data: np.ndarray) -> float:
    """
    Compute maximum absolute amplitude.

    Args:
        data: Input array

    Returns:
        Peak amplitude of the input array
    """
    max_amplitude = 0
    for sample in data:
        abs_value = abs(sample)
        if abs_value > max_amplitude:
            max_amplitude = abs_value
    return max_amplitude


@njit
def peak_amplitude_index(data: np.ndarray) -> int:
    """
    Compute index of peak amplitude.

    Args:
        data: Input array

    Returns:
        Index of peak amplitude
    """
    max_amplitude = 0
    index_peak = 0
    for index, sample in enumerate(data):
        abs_value = abs(sample)
        if abs_value > max_amplitude:
            max_amplitude = abs_value
            index_peak = index
    return index_peak


@njit
def is_above_threshold(data: np.ndarray, threshold: float) -> bool:
    """
    Checks if absolute amplitudes are above threshold.

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        True if input array is above threshold, otherwise False
    """
    for sample in data:
        if abs(sample) >= threshold:
            return True
    return False


@njit
def first_threshold_crossing(data: np.ndarray, threshold: float) -> Optional[int]:
    """
    Compute index of first threshold crossing.

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        Index of first threshold crossing. None if threshold was not exceeded
    """
    for index, sample in enumerate(data):
        if abs(sample) >= threshold:
            return index
    return None


@njit
def rise_time(
    data: np.ndarray,
    threshold: float,
    samplerate: int,
    first_crossing: Optional[int] = None,
    index_peak: Optional[int] = None,
) -> float:
    """
    Compute the rise time.

    The rise time is the time between the first threshold crossing and the peak amplitude.

    Args:
        data: Input array (hit)
        threshold: Threshold amplitude (in volts)
        samplerate: Sample rate of the input array
        first_crossing: Precomputed index of first threshold crossing to save computation time
        index_peak: Precomputed index of peak amplitude to save computation time
    """
    # save some computations if pre-results are provided
    n_first_crossing = (
        first_crossing
        if first_crossing is not None
        else first_threshold_crossing(data, threshold)
    )
    n_max = (
        index_peak
        if index_peak is not None
        else peak_amplitude_index(data)
    )
    return (n_max - n_first_crossing) / samplerate


@njit
def energy(data: np.ndarray, samplerate: int) -> float:
    """
    Compute the energy of a hit.

    Energy is the integral of the squared AE-signal over time (EN 1330-9).
    The unit of energy is eu. 1 eu corresponds to 1e-14 V²s.

    Args:
        data: Input array (hit)
        samplerate: Sample rate of input array in Hz

    Returns:
        Energy of input array (hit)
    """
    agg: float = 0
    for sample in data:
        agg += sample ** 2
    return agg * 1e14 / samplerate


@njit
def signal_strength(data: np.ndarray, samplerate: int) -> float:
    """
    Compute the signal strength of a hit.

    Signal strength is the integral of the rectified AE-signal over time.
    The unit of Signal Strength is nVs (1e-9 Vs).

    Args:
        data: Input array (hit)
        samplerate: Sample rate of input array in Hz

    Returns:
        Signal strength of input array (hit)
    """
    agg: float = 0
    for sample in data:
        agg += abs(sample)
    return agg * 1e9 / samplerate


@njit
def counts(data: np.ndarray, threshold: float) -> int:
    """
    Compute the number of positive threshold crossings of a hit (counts).

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        Number of positive threshold crossings
    """
    result: int = 0
    was_above_threshold: bool = False
    for sample in data:
        if sample >= threshold:
            if not was_above_threshold:
                result += 1
                was_above_threshold = True
        else:
            was_above_threshold = False
    return result


@njit
def rms(data: np.ndarray) -> float:
    """
    Compute the root mean square (RMS) of an array.

    Args:
        data: Input array

    Returns:
        RMS of the input array

    References:
        https://en.wikipedia.org/wiki/Root_mean_square
    """
    agg: float = 0
    for sample in data:
        agg += sample ** 2
    return math.sqrt(agg / len(data))
