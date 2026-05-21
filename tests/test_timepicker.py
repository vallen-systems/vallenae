from pathlib import Path

import numpy as np
import pytest

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
