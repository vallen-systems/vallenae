from pathlib import Path

import numpy as np
import pytest
import vallenae as vae
from numpy.testing import assert_allclose
from vallenae.io import TraRecord
from vallenae.io.tradb import _create_time_vector

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRADB = STEEL_PLATE_DIR / "sample.tradb"

TRAS_EXPECTED = [
    TraRecord(
        time=3.9927747,
        channel=2,
        param_id=3,
        pretrigger=500,
        threshold=100.469451121688,
        samplerate=5000000,
        samples=103488,
        data=np.empty(0),
        trai=2,
    ),
    TraRecord(
        time=3.992771,
        channel=3,
        param_id=4,
        pretrigger=500,
        threshold=100.469451121688,
        samplerate=5000000,
        samples=98960,
        data=np.empty(0),
        trai=1,
    ),
    TraRecord(
        time=3.9928129,
        channel=4,
        param_id=5,
        pretrigger=500,
        threshold=100.469451121688,
        samplerate=5000000,
        samples=96256,
        data=np.empty(0),
        trai=3,
    ),
    TraRecord(
        time=3.9928143,
        channel=1,
        param_id=2,
        pretrigger=500,
        threshold=100.469451121688,
        samplerate=5000000,
        samples=96944,
        data=np.empty(0),
        trai=4,
    ),
]

DATA_DIR = Path(__file__).resolve().parent / "data"
SIGNAL_TXT = DATA_DIR / "signal.txt"
SIGNAL_TRADB_RAW = DATA_DIR / "signal-raw.tradb"
SIGNAL_TRADB_FLAC = DATA_DIR / "signal-flac.tradb"


@pytest.fixture(name="sample_tradb")
def fixture_sample_tradb() -> vae.io.TraDatabase:
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
def fixture_signal_tradb_raw() -> vae.io.TraDatabase:
    with vae.io.TraDatabase(SIGNAL_TRADB_RAW) as tradb:
        yield tradb


@pytest.fixture(name="signal_tradb_flac")
def fixture_signal_tradb_flac() -> vae.io.TraDatabase:
    with vae.io.TraDatabase(SIGNAL_TRADB_FLAC) as tradb:
        yield tradb


@pytest.fixture(name="fresh_tradb")
def fixture_fresh_tradb(tmp_path) -> vae.io.TraDatabase:
    filename = tmp_path / "test.tradb"
    with vae.io.TraDatabase(filename, mode="rwc") as tradb:
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


def test_create_time_vector():
    fs = 1_000_000
    duration = 2.5
    n = duration * fs
    n_pretrigger = 1000
    t_pretrigger = n_pretrigger / fs
    t = _create_time_vector(n, fs, n_pretrigger)

    assert len(t) == n
    assert t[0] == -t_pretrigger
    assert t[-1] == pytest.approx(duration - t_pretrigger - 1 / fs)

    t_diff = np.diff(t)
    assert np.all(np.isclose(t_diff, 1 / fs))


def test_init():
    tradb = vae.io.TraDatabase(SAMPLE_TRADB)
    tradb.close()


def test_create(tmp_path):
    filename = tmp_path / "empty.tradb"
    vae.io.TraDatabase.create(filename)
    with vae.io.TraDatabase(filename) as tradb:
        assert tradb.tables() == {
            "tr_data",
            "tr_fieldinfo",
            "tr_params",
            "tr_globalinfo",
        }


def test_channel(sample_tradb):
    assert sample_tradb.channel() == {1, 2, 3, 4}


def test_iread_empty_database(fresh_tradb):
    assert list(fresh_tradb.iread()) == []


def test_iread_empty_query(sample_tradb):
    assert list(sample_tradb.iread(time_start=0, time_stop=0)) == []
    assert list(sample_tradb.iread(time_start=-1, time_stop=-1)) == []
    assert list(sample_tradb.iread(time_start=2, time_stop=1)) == []


@pytest.mark.parametrize("raw", [False, True])
def test_iread(sample_tradb, raw):
    tras = list(sample_tradb.iread(raw=raw))
    tras_expected_ordered = sorted(TRAS_EXPECTED, key=lambda t: t.trai)

    assert len(tras) == len(tras_expected_ordered)

    for tra, tra_expected in zip(tras, tras_expected_ordered):
        assert tra.time == pytest.approx(tra_expected.time)
        assert tra.channel == tra_expected.channel
        assert tra.param_id == tra_expected.param_id
        assert tra.pretrigger == tra_expected.pretrigger
        assert tra.threshold == pytest.approx(tra_expected.threshold / 1e6)
        assert tra.samplerate == tra_expected.samplerate
        assert tra.samples == tra_expected.samples
        assert tra.data.dtype == np.int16 if raw else np.float32
        assert tra.trai == tra_expected.trai
        assert tra.raw == raw


def test_iread_query_filter(sample_tradb):
    tras = list(sample_tradb.iread(query_filter="Samples >= 100000"))
    assert len(tras) == 1


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
    _, _, data_txt = signal_txt

    data_raw, _ = signal_tradb_raw.read_wave(1, time_axis=False)
    data_flac, _ = signal_tradb_flac.read_wave(1, time_axis=False)

    adc_step = max_amplitude * (2**-15)
    assert_allclose(data_txt, data_raw, atol=adc_step, rtol=0)
    assert_allclose(data_txt, data_flac, atol=adc_step, rtol=0)


@pytest.mark.parametrize("raw", [False, True])
def test_read_continuous_wave_dtype(sample_tradb, raw):
    y, _ = sample_tradb.read_continuous_wave(1, raw=raw)
    assert y.dtype == np.int16 if raw else np.float32


def test_read_continuous_wave_empty_tradb(fresh_tradb):
    y, t = fresh_tradb.read_continuous_wave(1)
    assert len(y) == 0
    assert len(t) == 0
    y, fs = fresh_tradb.read_continuous_wave(1, time_axis=False)
    assert len(y) == 0
    assert fs == 0


def test_read_continuous_wave(fresh_tradb):
    trai = 0

    def write_time_axis(samplerate, samples, sets, t_start=0):
        # create time axis
        y = t_start + np.arange(0, samples * sets, dtype=np.float32) / samplerate
        # write time axis blockwise
        for data in np.reshape(y, (-1, sets)):
            nonlocal trai
            trai += 1
            t = data[0]
            fresh_tradb.write(
                TraRecord(
                    time=t,
                    channel=1,
                    param_id=1,
                    pretrigger=0,
                    threshold=0,
                    samplerate=samplerate,
                    samples=samples,
                    data=data,
                    trai=trai,
                )
            )
        return y

    samplerate = 100
    samples = 10
    sets = 10

    # write data from t = [0, 1)
    ref1 = write_time_axis(samplerate, samples, sets)

    # get total time range
    y, t = fresh_tradb.read_continuous_wave(1)
    assert y.dtype == np.float32
    assert t.dtype == np.float32
    assert y.shape == (samples * sets,)
    assert t.shape == y.shape
    assert_allclose(y, ref1, atol=1e-6)
    assert_allclose(t, ref1, atol=1e-6)

    _, fs = fresh_tradb.read_continuous_wave(1, time_axis=False)
    assert fs == samplerate

    # get empty time range
    y, t = fresh_tradb.read_continuous_wave(1, time_start=0.1, time_stop=0.1)
    assert len(y) == 0
    assert len(t) == 0
    y, t = fresh_tradb.read_continuous_wave(1, time_start=-0.1, time_stop=-0.1)
    assert len(y) == 0
    assert len(t) == 0

    # write data from t = [2, 3) -> time gap
    ref2 = write_time_axis(samplerate, samples, sets, t_start=2)
    ref2_total = np.concatenate([ref1, np.zeros(samples * sets), ref2])

    # get total time range (with gap)
    y, _ = fresh_tradb.read_continuous_wave(1)
    assert y.shape == ref2_total.shape
    assert_allclose(y, ref2_total, atol=1e-6)

    # get exact time range
    y, t = fresh_tradb.read_continuous_wave(1, time_start=2.18, time_stop=2.55)
    assert len(y) == 37  # = (2.55 - 2.18) * samplerate
    assert y[0] == pytest.approx(2.18)
    assert y[-1] == pytest.approx(2.54)  # = 2.55 - 1/fs
    assert t[0] == pytest.approx(2.18)

    # get exact time range < 1 block (0.1 s)
    y, t = fresh_tradb.read_continuous_wave(1, time_start=2.13, time_stop=2.18)
    assert len(y) == 5
    assert y[0] == pytest.approx(2.13)
    assert y[-1] == pytest.approx(2.17)  # = 2.18 - 1/fs
    assert t[0] == pytest.approx(2.13)

    # get time range exceeding lower bound
    y, t = fresh_tradb.read_continuous_wave(1, time_start=1.9, time_stop=2.4)
    assert len(y) == 50  # = (2.4 - 1.9) * samplerate
    assert y[0] == 0  # zero padded
    assert y[-1] == pytest.approx(2.39)  # = 2.4 - 1/fs
    assert t[0] == pytest.approx(1.9)

    # get time range exceeding lower / upper bounds
    y, t = fresh_tradb.read_continuous_wave(1, time_start=-0.1)
    assert_allclose(y, np.concatenate([np.zeros(10), ref2_total]), atol=1e-6)
    assert t[0] == pytest.approx(-0.1)
    y, t = fresh_tradb.read_continuous_wave(1, time_stop=4)
    assert_allclose(y, np.concatenate([ref2_total, np.zeros(100)]), atol=1e-6)
    assert t[0] == pytest.approx(0.0)


def test_listen(sample_tradb):
    assert len(list(sample_tradb.listen())) == 0
    assert len(list(sample_tradb.listen(existing=True))) == 4
    assert [tra.trai for tra in sample_tradb.listen(existing=True)] == [2, 1, 3, 4]


def test_write(fresh_tradb):
    new_tra = TraRecord(
        time=11.11,
        channel=1,
        param_id=1,
        pretrigger=500,
        threshold=111,
        samplerate=5000000,
        samples=103488,
        data=np.empty(0, dtype=np.float32),
        trai=1,
        raw=False,
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
    # assert tra_read.data == new_tra.data
    assert tra_read.trai == new_tra.trai
    assert tra_read.raw is False

    fresh_tradb.write(new_tra)
    assert fresh_tradb.rows() == 2  # duplicate TRAI, no exception?
