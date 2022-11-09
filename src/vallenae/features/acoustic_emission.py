from typing import Optional

import numpy as np


def peak_amplitude(data: np.ndarray) -> float:
    """
    Compute maximum absolute amplitude.

    Args:
        data: Input array

    Returns:
        Peak amplitude of the input array
    """
    return np.max(np.abs(data))


def peak_amplitude_index(data: np.ndarray) -> int:
    """
    Compute index of peak amplitude.

    Args:
        data: Input array

    Returns:
        Index of peak amplitude
    """
    return np.argmax(np.abs(data))


def _mask_above_threshold(data: np.ndarray, threshold: float) -> np.ndarray:
    return (data >= threshold) | (data <= -threshold)


def is_above_threshold(data: np.ndarray, threshold: float) -> bool:
    """
    Checks if absolute amplitudes are above threshold.

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        True if input array is above threshold, otherwise False
    """
    return np.any(_mask_above_threshold(data, threshold))


def first_threshold_crossing(data: np.ndarray, threshold: float) -> Optional[int]:
    """
    Compute index of first threshold crossing.

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        Index of first threshold crossing. None if threshold was not exceeded
    """
    above_threshold = _mask_above_threshold(data, threshold)
    index = np.argmax(above_threshold)
    return index if above_threshold[index] else None


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
    if n_first_crossing is None:
        return 0
    return (n_max - n_first_crossing) / samplerate


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
    return np.sum(data ** 2) * 1e14 / samplerate


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
    return np.sum(np.abs(data)) * 1e9 / samplerate


def counts(data: np.ndarray, threshold: float) -> int:
    """
    Compute the number of positive threshold crossings of a hit (counts).

    Args:
        data: Input array
        threshold: Threshold amplitude

    Returns:
        Number of positive threshold crossings
    """
    above_positive_threshold = data >= threshold
    return np.count_nonzero(~above_positive_threshold[:-1] & above_positive_threshold[1:])


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
    return np.sqrt(np.mean(data ** 2))
