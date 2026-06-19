from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

import vallenae as vae
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

    t_expected = (np.arange(n) - n_pretrigger) / fs
    assert_allclose(t, t_expected)


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


FS = 100  # sample rate of the time_signal_tradb fixture
DATA_END = 3.0  # data spans t = [0, 1) and [2, 3); open bounds resolve to [0.0, 3.0)


@pytest.fixture(name="time_signal_tradb")
def fixture_time_signal_tradb(fresh_tradb):
    """Channel 1 where each sample's value equals its time, over t = [0, 1) and [2, 3) (gap)."""
    trai = 0
    for t_offset in (0.0, 2.0):
        times = t_offset + np.arange(100, dtype=np.float32) / FS  # 1 s of "value == time"
        for block in np.split(times, 10):  # 10 records of 10 samples each
            trai += 1
            fresh_tradb.write(
                TraRecord(
                    time=float(block[0]),
                    channel=1,
                    param_id=1,
                    pretrigger=0,
                    threshold=0,
                    samplerate=FS,
                    samples=len(block),
                    data=block,
                    trai=trai,
                )
            )
    return fresh_tradb


@pytest.mark.parametrize(
    ("time_start", "time_stop"),
    [
        (None, None),  # full range (with gap)
        (0.0, 1.0),  # first data block only
        (2.18, 2.55),  # exact range inside the second block
        (2.13, 2.18),  # sub-record range (< 0.1 s)
        (1.9, 2.4),  # exceeds lower bound -> leading zeros across the gap
        (-0.1, None),  # exceeds lower bound, open stop
        (None, 4.0),  # open start, exceeds upper bound -> trailing zeros
        (5.0, 6.0),  # window entirely after the data -> all zeros
        (-2.0, -1.0),  # window entirely before the data -> all zeros
    ],
)
def test_read_continuous_wave_content(time_signal_tradb, time_start, time_stop):
    y, t = time_signal_tradb.read_continuous_wave(
        1, time_start=time_start, time_stop=time_stop, show_progress=False
    )
    ts = 0.0 if time_start is None else time_start
    tp = DATA_END if time_stop is None else time_stop
    assert len(y) == round(tp * FS) - round(ts * FS)
    assert t[0] == pytest.approx(ts)
    # value == time where data exists (sample indices [0, 100) and [200, 300)), else 0
    idx = round(ts * FS) + np.arange(len(y))
    in_data = ((idx >= 0) & (idx < 100)) | ((idx >= 200) & (idx < 300))
    assert_allclose(y[in_data], t[in_data], atol=1e-6)  # signal equals the time axis
    assert_allclose(y[~in_data], 0, atol=1e-6)


def test_read_continuous_wave_axis_and_rate(time_signal_tradb):
    y, t = time_signal_tradb.read_continuous_wave(
        1, time_start=0.0, time_stop=1.0, show_progress=False
    )
    assert y.dtype == np.float32
    assert t.dtype == np.float64  # time axis is float64 (precision at high sample rates)
    assert_allclose(t, np.arange(100) / FS, atol=1e-6)  # time axis values
    _, fs = time_signal_tradb.read_continuous_wave(1, time_axis=False, show_progress=False)
    assert fs == FS


@pytest.mark.parametrize("time", [0.1, -0.1])
def test_read_continuous_wave_empty_range(time_signal_tradb, time):
    # time_start == time_stop -> zero-length output
    y, t = time_signal_tradb.read_continuous_wave(
        1, time_start=time, time_stop=time, show_progress=False
    )
    assert len(y) == 0
    assert len(t) == 0


def write_tra(tradb, trai, time, n_samples, samplerate, value, channel=1):
    """Write a single transient record with constant data == value."""
    tradb.write(
        TraRecord(
            time=time,
            channel=channel,
            param_id=channel,
            pretrigger=0,
            threshold=0,
            samplerate=samplerate,
            samples=n_samples,
            data=np.full(n_samples, float(value), dtype=np.float32),
            trai=trai,
        )
    )


def test_iread_time_range_record_selection(fresh_tradb):
    # records spanning t = [k*0.1, k*0.1 + 0.1) for k = 0..4 (fs=100, 10 samples each)
    for k in range(5):
        write_tra(fresh_tradb, trai=k + 1, time=k * 0.1, n_samples=10, samplerate=100, value=1)

    def trais(time_start, time_stop):
        return sorted(
            t.trai for t in fresh_tradb.iread(channel=1, time_start=time_start, time_stop=time_stop)
        )

    # include the record straddling time_start (0.1 contains 0.15) and the one at time_stop (0.3)
    assert trais(0.15, 0.30) == [2, 3, 4]
    # a window fully inside the last record must still return it (empty-range guard regression)
    assert trais(0.43, 0.47) == [5]


def test_read_continuous_wave_length_invariant(fresh_tradb):
    # burst at an awkward (non sample-aligned) time, fs=1000
    write_tra(fresh_tradb, trai=1, time=0.015837917, n_samples=4, samplerate=1000, value=1)
    time_start, time_stop = 0.015347917, 0.022829461
    y, _ = fresh_tradb.read_continuous_wave(
        1, time_start=time_start, time_stop=time_stop, show_progress=False
    )
    expected = round(time_stop * 1000) - round(time_start * 1000)
    assert len(y) == expected


def test_read_continuous_wave_samplerate_differs_from_timebase(fresh_tradb):
    # The DB TimeBase (1e7) is NOT the record SampleRate: length and time axis must
    # be derived from the record SampleRate (not `samplerate = self._timebase`).
    fs = 2_000_000  # 2 MHz, != TimeBase (1e7)
    n = 100
    write_tra(fresh_tradb, trai=1, time=0.0, n_samples=n, samplerate=fs, value=1)
    y, t = fresh_tradb.read_continuous_wave(
        1, time_start=0.0, time_stop=n / fs, show_progress=False
    )
    assert len(y) == n  # NOT n * (1e7 / fs)
    assert_allclose(y, np.ones(n, dtype=np.float32))
    assert t[1] - t[0] == pytest.approx(1 / fs)


def test_read_continuous_wave_mixed_samplerate_raises(fresh_tradb):
    # two records on one channel with different sample rates cannot form one array
    write_tra(fresh_tradb, trai=1, time=0.0, n_samples=10, samplerate=100, value=1)
    write_tra(fresh_tradb, trai=2, time=0.1, n_samples=10, samplerate=200, value=2)
    with pytest.raises(RuntimeError):
        fresh_tradb.read_continuous_wave(1, show_progress=False)


def test_simultaneous_channels_at_time_boundary(fresh_tradb):
    # Two channels with records sharing the SAME Time tick (simultaneous hits):
    # TRAI 1->1@0.10, 2->2@0.10, 3->1@0.20, 4->2@0.20, 5->1@0.30, 6->2@0.30 (fs=100, 10 samples).
    fresh_tradb.connection().execute(
        "INSERT INTO tr_params (ID, SetupID, Chan, ADC_µV, TR_mV) VALUES (2, 1, 2, 1, 1)"
    )
    trai = 0
    for time in (0.10, 0.20, 0.30):
        for channel in (1, 2):
            trai += 1
            write_tra(fresh_tradb, trai, time, 10, 100, value=channel, channel=channel)

    # time_start lands on a timestamp shared by both channels; channel 1's record at 0.20
    # (TRAI 3) must not be dropped by the lower TRAI bound.
    trais = sorted(t.trai for t in fresh_tradb.iread(channel=1, time_start=0.20, time_stop=0.35))
    assert trais == [3, 5]  # channel-1 records at 0.20 and 0.30

    # a window starting exactly on a shared timestamp must return channel 1's data, not 0
    y, _ = fresh_tradb.read_continuous_wave(1, time_start=0.20, time_stop=0.30, show_progress=False)
    assert_allclose(y, np.ones(10, dtype=np.float32))  # the channel-1 hit at 0.20


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
