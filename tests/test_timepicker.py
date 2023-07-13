from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose
from vallenae import timepicker
from vallenae.io import TraDatabase

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRADB = STEEL_PLATE_DIR / "sample.tradb"
TRAI = 4


@pytest.fixture(name="waveform", scope="module")
def fixture_waveform() -> np.ndarray:
    with TraDatabase(SAMPLE_TRADB) as tradb:
        wave, _ = tradb.read_wave(TRAI)
        yield wave[:5000]  # crop signal


def test_hinkley(waveform):
    result, index = timepicker.hinkley(waveform, alpha=5)
    assert len(result) == len(waveform)
    assert index == 846
    assert np.argmin(result) == index

    # test different alpha value
    result, index = timepicker.hinkley(waveform, alpha=10)
    assert index == 837  # A0


def test_aic(waveform):
    result, index = timepicker.aic(waveform)
    assert len(result) == len(waveform)
    assert index == 495  # S0
    assert np.nanargmin(result) == index


def test_energy_ratio(waveform):
    result, index = timepicker.energy_ratio(waveform, win_len=100)
    assert len(result) == len(waveform)
    assert index == 489  # S0
    assert np.argmax(result) == index


def test_modified_energy_ratio(waveform):
    result, index = timepicker.modified_energy_ratio(waveform, win_len=100)
    assert len(result) == len(waveform)
    assert index == 821  # A0
    assert np.argmax(result) == index


@pytest.mark.parametrize(
    ("func_numba", "func_numpy"),
    [
        (timepicker._hinkley_numba, timepicker._hinkley_numpy),
        (timepicker._aic_numba, timepicker._aic_numpy),
        (timepicker._energy_ratio_numba, timepicker._energy_ratio_numpy),
    ],
)
def test_implementations(waveform, func_numba, func_numpy):
    result_numba, index_numba = func_numba(waveform)
    result_numpy, index_numpy = func_numpy(waveform)
    assert index_numba == index_numpy
    assert_allclose(result_numba, result_numpy, rtol=1e-6, atol=1e-9)
