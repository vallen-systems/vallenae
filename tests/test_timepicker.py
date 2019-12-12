import math
from pathlib import Path
import numpy as np
from numpy.testing import assert_allclose
import pytest

from vallenae.io import TraDatabase
from vallenae.timepicker import (
    hinkley,
    aic,
    energy_ratio,
    modified_energy_ratio,
)


STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRADB = STEEL_PLATE_DIR / "sample.tradb"
TRAI = 4


@pytest.fixture(name="waveform", scope="module")
def fixture_waveform() -> np.ndarray:
    with TraDatabase(SAMPLE_TRADB) as tradb:
        wave, _ = tradb.read_wave(TRAI)
        yield wave[:5000]  # crop signal


def test_hinkley(waveform):
    result, index = hinkley(waveform, alpha=5)
    assert len(result) == len(waveform)
    assert index == 846
    assert np.argmin(result) == index
    
    # test different alpha value
    result, index = hinkley(waveform, alpha=10)
    assert index == 837  # A0


def test_aic(waveform):
    def aic_naive(arr: np.ndarray):
        n = len(arr)
        result = np.full(n, np.nan, dtype=np.float32)
        for i in range(n - 1):
            l_variance = np.var(arr[: i + 1])
            r_variance = np.var(arr[i + 1:])
            if l_variance > 0.0 and r_variance > 0.0:
                result[i] = i * math.log10(l_variance) + (n - i - 1) * math.log10(r_variance)
            else:
                result[i] = np.nan
        return result, np.argmin(result)

    result, index = aic(waveform)
    assert len(result) == len(waveform)
    assert index == 495  # S0

    result_naive, index_naive = aic(waveform)
    assert index == index_naive
    assert_allclose(result, result_naive)


def test_energy_ratio(waveform):
    result, index = energy_ratio(waveform, win_len=100)
    assert len(result) == len(waveform)
    assert index == 489  # S0
    assert np.argmax(result) == index


def test_modified_energy_ratio(waveform):
    result, index = modified_energy_ratio(waveform, win_len=100)
    assert len(result) == len(waveform)
    assert index == 821  # A0
    assert np.argmax(result) == index
