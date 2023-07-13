import math
import random
from typing import Optional, Tuple

import numpy as np
import pytest
from vallenae.features import (
    amplitude_to_db,
    counts,
    db_to_amplitude,
    energy,
    first_threshold_crossing,
    is_above_threshold,
    peak_amplitude,
    peak_amplitude_index,
    rise_time,
    rms,
    signal_strength,
)

LEN: int = 100
SAMPLERATES: Tuple[int] = (1, 10, int(1e6))


@pytest.fixture(name="random_array", scope="module")
def fixture_random_array():
    return np.random.rand(LEN)


def test_db_conversion():
    # 0 dB(AE) = 1 µV
    assert amplitude_to_db(1e-6) == 0
    assert db_to_amplitude(0) == 1e-6
    # 120 dB(AE) = 1 V?
    assert amplitude_to_db(1) == 120
    assert db_to_amplitude(120) == 1


def test_peak_amplitude(random_array):
    def naive(data: np.ndarray) -> float:
        return np.max(np.abs(data))

    assert peak_amplitude(random_array) == naive(random_array)

    # test negative amplitude
    arr = np.ones(5)
    arr[3] = -10
    assert peak_amplitude(arr) == naive(arr)


def test_peak_amplitude_index(random_array):
    def naive(data: np.ndarray) -> int:
        return np.argmax(np.abs(data))

    assert peak_amplitude_index(random_array) == naive(random_array)


def test_is_above_threshold():
    # def naive(data: np.ndarray, threshold: float) -> bool:
    #     return np.max(data) >= threshold

    arr = np.random.rand(LEN)
    assert is_above_threshold(arr, -1)
    assert is_above_threshold(arr, 0)
    arr[-1] = 1
    assert is_above_threshold(arr, 1)
    arr[0] = 2
    assert is_above_threshold(arr, 2)
    assert not is_above_threshold(arr, 2.01)


def test_first_threshold_crossing():
    def naive(data: np.ndarray, threshold: float) -> Optional[int]:
        above_threshold = np.abs(data) >= threshold
        index = np.argmax(
            above_threshold
        )  # = 0 if no crossing was found, might be the first sample though
        if index == 0 and not above_threshold[0]:
            return None
        return index

    arr = np.zeros(LEN)
    assert first_threshold_crossing(arr, 1.0) is None

    arr = np.random.rand(LEN)
    thr = abs(random.random())
    assert first_threshold_crossing(arr, thr) == naive(arr, thr)

    arr[0] = 1
    thr = 1
    assert first_threshold_crossing(arr, thr) == 0

    arr[-1] = 2
    thr = 2
    assert first_threshold_crossing(arr, thr) == LEN - 1


@pytest.mark.parametrize("samplerate", SAMPLERATES)
def test_rise_time(samplerate: int):
    arr = np.random.rand(LEN)

    arr[0] = 2
    assert rise_time(arr, 2, samplerate) == 0

    arr[-1] = 3
    assert rise_time(arr, 0, samplerate) == (LEN - 1) / samplerate


@pytest.mark.parametrize("samplerate", SAMPLERATES)
def test_energy(random_array, samplerate: int):
    def naive(data: np.ndarray, samplerate: int) -> float:
        return np.sum(data**2) * 1e14 / samplerate

    assert energy(random_array, samplerate) == pytest.approx(naive(random_array, samplerate))


@pytest.mark.parametrize("samplerate", SAMPLERATES)
def test_signal_strength(random_array, samplerate: int):
    def naive(data: np.ndarray, samplerate: int) -> float:
        return np.sum(abs(data)) * 1e9 / samplerate

    assert signal_strength(random_array, samplerate) == pytest.approx(
        naive(random_array, samplerate)
    )


def test_counts(random_array):
    def naive(data: np.ndarray, threshold: float) -> int:
        above_positive_threshold = (data >= threshold).astype(int)
        return np.count_nonzero(np.diff(above_positive_threshold) == 1)

    arr = np.zeros(LEN)
    assert counts(arr, 0) == 0
    assert counts(arr, 0.5) == 0

    # ignore if first sample is above threshold
    arr[0] = 1
    assert counts(arr, 0.5) == 0

    # ignore negative threshold crossings
    arr[2] = -1
    assert counts(arr, 0.5) == 0

    arr[-1] = 1
    assert counts(arr, 0.5) == 1

    for threshold in (-1, 0, 0.5, 1):
        assert counts(random_array, threshold) == naive(random_array, threshold)


def test_rms(random_array):
    def naive(data: np.ndarray):
        return math.sqrt(np.sum(data**2) / len(data))

    assert rms(random_array) == pytest.approx(naive(random_array))
