import os
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

import vallenae as vae
from vallenae.io import TraRecord
from vallenae.io.tradb import create_empty_tradb

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRADB = STEEL_PLATE_DIR / "sample.tradb"

TRAS_EXPECTED = [
    TraRecord(
        time=3.9927747, channel=2, param_id=3, pretrigger=500, threshold=100.469451121688,
        samplerate=5000000, samples=103488, data_format=2, data=np.empty(0), trai=2
    ),
    TraRecord(
        time=3.992771, channel=3, param_id=4, pretrigger=500, threshold=100.469451121688,
        samplerate=5000000, samples=98960, data_format=2, data=np.empty(0), trai=1
    ),
    TraRecord(
        time=3.9928129, channel=4, param_id=5, pretrigger=500, threshold=100.469451121688,
        samplerate=5000000, samples=96256, data_format=2, data=np.empty(0), trai=3
    ),
    TraRecord(
        time=3.9928143, channel=1, param_id=2, pretrigger=500, threshold=100.469451121688,
        samplerate=5000000, samples=96944, data_format=2, data=np.empty(0), trai=4
    ),
]

DATA_DIR = Path(__file__).resolve().parent / "data"
SIGNAL_TXT = DATA_DIR / "signal.txt"
SIGNAL_TRADB_RAW = DATA_DIR / "signal-raw.tradb"
SIGNAL_TRADB_FLAC = DATA_DIR / "signal-flac.tradb"


@pytest.fixture(name="sample_tradb")
def fixture_sample_tradb() -> vae.io.PriDatabase:
    with vae.io.TraDatabase(SAMPLE_TRADB) as tradb:
        yield tradb


@pytest.fixture(name="signal_txt")
def fixture_signal_txt():
    with open(SIGNAL_TXT, "r") as f:
        dt = float(f.readline().strip())
        samples = int(f.readline().strip())
    signal = np.genfromtxt(SIGNAL_TXT, skip_header=2)
    return dt, samples, signal


@pytest.fixture(name="signal_tradb_raw")
def fixture_signal_tradb_raw() -> vae.io.PriDatabase:
    with vae.io.TraDatabase(SIGNAL_TRADB_RAW) as tradb:
        yield tradb


@pytest.fixture(name="signal_tradb_flac")
def fixture_signal_tradb_flac() -> vae.io.PriDatabase:
    with vae.io.TraDatabase(SIGNAL_TRADB_FLAC) as tradb:
        yield tradb


@pytest.fixture(name="fresh_tradb")
def fixture_fresh_tradb() -> vae.io.TraDatabase:
    filename = "test.tradb"
    create_empty_tradb(filename)
    tradb = vae.io.TraDatabase(filename, readonly=False)
    # add parameter
    con = tradb.connection()
    con.execute(
        """
        INSERT INTO tr_params (
            ID, SetupID, Chan, ADC_µV, TR_mV
        ) VALUES (
            1, 1, 1, 1, 1
        )
        """
    )

    yield tradb
    tradb.close()
    os.remove(filename)


def test_init():
    pridb = vae.io.TraDatabase(SAMPLE_TRADB)
    pridb.close()


def test_channel(sample_tradb):
    assert sample_tradb.channel() == {1, 2, 3, 4}


def test_iread(sample_tradb):
    tras = list(sample_tradb.iread())

    assert len(tras) == len(TRAS_EXPECTED)

    for tra, tra_expected in zip(tras, TRAS_EXPECTED):
        assert tra.time == pytest.approx(tra_expected.time)
        assert tra.channel == tra_expected.channel
        assert tra.param_id == tra_expected.param_id
        assert tra.pretrigger == tra_expected.pretrigger
        assert tra.threshold == pytest.approx(tra_expected.threshold / 1e6)
        assert tra.samplerate == tra_expected.samplerate
        assert tra.samples == tra_expected.samples
        assert tra.data_format == tra_expected.data_format
        assert tra.trai == tra_expected.trai


def test_read(sample_tradb):
    df = sample_tradb.read()

    assert len(df) == len(TRAS_EXPECTED)
    assert df.index.name == "trai"


def test_read_wave_time_axis(sample_tradb):
    tra = next(iter(sample_tradb.iread(trai=1)))
    _, t = sample_tradb.read_wave(1, time_axis=True)

    assert len(t) == tra.samples
    assert min(t) == pytest.approx(float(-tra.pretrigger) / tra.samplerate)
    assert max(t) == pytest.approx(float(tra.samples - tra.pretrigger - 1) / tra.samplerate)


def test_read_wave_compare_results_raw_flac(signal_tradb_raw, signal_tradb_flac):
    data_raw, fs_raw = signal_tradb_raw.read_wave(1, time_axis=False)
    data_flac, fs_flac = signal_tradb_flac.read_wave(1, time_axis=False)

    assert fs_raw == fs_flac
    assert_allclose(data_raw, data_flac)


def test_read_wave_compare_to_reference_txt(signal_txt, signal_tradb_raw, signal_tradb_flac):
    max_amplitude = 1
    dt, samples, data_txt = signal_txt

    data_raw, _ = signal_tradb_raw.read_wave(1, time_axis=False)
    data_flac, _ = signal_tradb_flac.read_wave(1, time_axis=False)

    adc_step = max_amplitude * (2 ** -15)
    assert_allclose(data_txt, data_raw, atol=adc_step, rtol=0)
    assert_allclose(data_txt, data_flac, atol=adc_step, rtol=0)


def test_write(fresh_tradb):
    new_tra = TraRecord(
        time=11.11, channel=1, param_id=1, pretrigger=500, threshold=111,
        samplerate=5000000, samples=103488,
        data_format=2, data=np.empty(0, dtype=np.float32), trai=1,
    )

    assert fresh_tradb.rows() == 0
    fresh_tradb.write(new_tra)
    assert fresh_tradb.rows() == 1

    tra_read = next(iter(fresh_tradb.iread()))
    assert tra_read.time == new_tra.time
    assert tra_read.channel == new_tra.channel
    assert tra_read.param_id == new_tra.param_id
    assert tra_read.pretrigger == new_tra.pretrigger
    assert tra_read.threshold == new_tra.threshold
    assert tra_read.samplerate == new_tra.samplerate
    assert tra_read.samples == new_tra.samples
    assert tra_read.data_format == 0  # setting in TraDatabase class
    # assert tra_read.data == new_tra.data
    assert tra_read.trai == new_tra.trai

    fresh_tradb.write(new_tra)
    assert fresh_tradb.rows() == 2  # duplicate TRAI, no exception?
