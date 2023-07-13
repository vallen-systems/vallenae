import numpy as np
import pytest
from vallenae import features, timepicker
from vallenae.io import compression


@pytest.fixture()
def random_array():
    rng = np.random.default_rng(42)
    return rng.random(65536)


@pytest.mark.benchmark(group="features")
@pytest.mark.parametrize(
    "function",
    [
        lambda y: features.peak_amplitude(y),
        lambda y: features.rise_time(y, threshold=0.5, samplerate=1_000_000),
        lambda y: features.counts(y, threshold=0.5),
        lambda y: features.energy(y, samplerate=1_000_000),
        lambda y: features.signal_strength(y, samplerate=1_000_000),
        lambda y: features.rms(y),
    ],
    ids=(
        "peak_amplitude",
        "rise_time",
        "counts",
        "energy",
        "signal_strength",
        "rms",
    ),
)
def test_benchmark_features(benchmark, random_array, function):
    benchmark(function, random_array)


@pytest.mark.benchmark(group="timepicker")
@pytest.mark.parametrize(
    "function",
    [
        timepicker._hinkley_numba,
        timepicker._hinkley_numpy,
        timepicker._aic_numba,
        timepicker._aic_numpy,
        timepicker._energy_ratio_numba,
        timepicker._energy_ratio_numpy,
        timepicker.modified_energy_ratio,
    ],
)
def test_benchmark_timepicker(benchmark, random_array, function):
    benchmark(function, random_array)


@pytest.mark.parametrize("data_format", [0, 2])
def test_benchmark_encode(benchmark, random_array, data_format):
    benchmark(compression.encode_data_blob, random_array, data_format, 0.1)
