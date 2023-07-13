from pathlib import Path

import pytest
import vallenae as vae
from numpy import dtype, float64, int64
from pandas import Int64Dtype
from vallenae.io import HitRecord, MarkerRecord, ParametricRecord, StatusRecord

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
PRIDB_FILE_PATH = STEEL_PLATE_DIR / "sample.pridb"

LABELS_EXPECTED = [
    "",
    "10:52 Resume",
    "2019-09-20 10:54:52",
    "TimeZone: +02:00 (W. Europe Standard Time)",
    "10:56 Suspend",
]

# Caution: units are µV and µs (except time)
HITS_EXPECTED = [
    HitRecord(
        set_id=10,
        time=3.992771,
        channel=3,
        param_id=4,
        threshold=100.469451,
        amplitude=46538.6675710947,
        rise_time=49.5,
        duration=19671.6,
        energy=27995100.3052212,
        signal_strength=29064.1915258135,
        rms=5.05799020605523,
        counts=2180,
        trai=1,
        cascade_hits=4,
        cascade_counts=2193,
        cascade_energy=27995448.6329966,
        cascade_signal_strength=29131.710036357,
    ),
    HitRecord(
        set_id=11,
        time=3.9927747,
        channel=2,
        param_id=3,
        threshold=100.469451,
        amplitude=59621.0079186672,
        rise_time=192.1,
        duration=20575.7,
        energy=22762787.1460552,
        signal_strength=24734.02914512,
        rms=5.02806126992473,
        counts=2047,
        trai=2,
        cascade_hits=4,
        cascade_counts=2054,
        cascade_energy=22762918.7161395,
        cascade_signal_strength=24761.7395309888,
    ),
    HitRecord(
        set_id=12,
        time=3.9928129,
        channel=4,
        param_id=5,
        threshold=100.469451,
        amplitude=34118.5122422787,
        rise_time=354.6,
        duration=19130.7,
        energy=12867002.8866017,
        signal_strength=19956.3935214563,
        rms=4.8085824049677,
        counts=1854,
        trai=3,
        cascade_hits=4,
        cascade_counts=1858,
        cascade_energy=12867202.6824819,
        cascade_signal_strength=19997.9738662233,
    ),
    HitRecord(
        set_id=13,
        time=3.9928143,
        channel=1,
        param_id=2,
        threshold=100.469451,
        amplitude=29114.8291235365,
        rise_time=160.3,
        duration=19266.1,
        energy=12652748.5220513,
        signal_strength=20545.4817939854,
        rms=4.90834552540271,
        counts=1985,
        trai=4,
        cascade_hits=5,
        cascade_counts=1988,
        cascade_energy=12652874.448889,
        cascade_signal_strength=20573.5164221492,
    ),
]

PARAMETRIC_EXPECTED = [
    ParametricRecord(set_id=5, time=0.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=6, time=1.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=7, time=2.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=8, time=3.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=9, time=3.99, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=14, time=4.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=15, time=5.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=16, time=6.0, param_id=1, pctd=0, pcta=0),
    ParametricRecord(set_id=17, time=6.45, param_id=1, pctd=0, pcta=0),
]


@pytest.fixture(name="sample_pridb")
def fixture_sample_pridb() -> vae.io.PriDatabase:
    pridb = vae.io.PriDatabase(PRIDB_FILE_PATH)
    yield pridb
    pridb.close()


@pytest.fixture(name="fresh_pridb")
def fixture_fresh_pridb(tmp_path) -> vae.io.PriDatabase:
    filename = tmp_path / "test.pridb"
    with vae.io.PriDatabase(filename, mode="rwc") as pridb:
        con = pridb.connection()
        con.execute(
            """
            INSERT INTO ae_params (
                ID, SetupID, Chan, ADC_µV, ADC_TE, ADC_SS
            ) VALUES (
                1, 1, 1, 1, 1, 1
            )
            """
        )
        yield pridb


def test_init():
    pridb = vae.io.PriDatabase(PRIDB_FILE_PATH)
    pridb.close()


def test_create(tmp_path):
    filename = tmp_path / "empty.pridb"
    vae.io.PriDatabase.create(filename)
    with vae.io.PriDatabase(filename) as pridb:
        assert pridb.tables() == {
            "acq_setup",
            "ae_data",
            "ae_fieldinfo",
            "ae_globalinfo",
            "ae_markers",
            "ae_params",
            "data_integrity",
        }


def test_channel(sample_pridb):
    assert sample_pridb.channel() == {1, 2, 3, 4}


def test_iread_markers(sample_pridb):
    iterable = sample_pridb.iread_markers()
    labels = [marker.data for marker in iterable]

    assert len(iterable) == len(LABELS_EXPECTED)
    assert len(labels) == len(LABELS_EXPECTED)
    assert labels == LABELS_EXPECTED


def test_iread_markers_query_filter(sample_pridb):
    markers = list(sample_pridb.iread_markers(query_filter="Data LIKE '%TimeZone%'"))
    assert len(markers) == 1


def test_read_markers(sample_pridb):
    markers = sample_pridb.read_markers()

    assert len(markers) == len(LABELS_EXPECTED)
    assert markers.index.name == "set_id"
    assert markers.index.dtype == int64
    assert dict(markers.dtypes) == {
        "time": float64,
        "set_type": Int64Dtype(),
        "number": Int64Dtype(),
        "data": dtype("O"),
    }

    labels = list(markers["data"])
    assert labels == LABELS_EXPECTED


def test_iread_hits(sample_pridb):
    hits = list(sample_pridb.iread_hits())

    assert len(hits) == len(HITS_EXPECTED)

    for hit, hit_expected in zip(hits, HITS_EXPECTED):
        assert hit.set_id == hit_expected.set_id
        assert hit.time == pytest.approx(hit_expected.time)
        assert hit.channel == hit_expected.channel
        assert hit.threshold == pytest.approx(hit_expected.threshold / 1e6)
        assert hit.amplitude == pytest.approx(hit_expected.amplitude / 1e6)
        assert hit.rise_time == pytest.approx(hit_expected.rise_time / 1e6)
        assert hit.duration == pytest.approx(hit_expected.duration / 1e6)
        assert hit.energy == pytest.approx(hit_expected.energy)
        assert hit.signal_strength == pytest.approx(hit_expected.signal_strength)
        assert hit.rms == pytest.approx(hit_expected.rms / 1e6)
        assert hit.counts == hit_expected.counts
        assert hit.trai == hit_expected.trai
        assert hit.cascade_hits == hit_expected.cascade_hits
        assert hit.cascade_counts == hit_expected.cascade_counts
        assert hit.cascade_energy == pytest.approx(hit_expected.cascade_energy)
        assert hit.cascade_signal_strength == pytest.approx(hit_expected.cascade_signal_strength)


def test_iread_hits_query_filter(sample_pridb):
    hits = list(sample_pridb.iread_hits(query_filter="SetID >= 12"))
    assert len(hits) == 2


def test_read_hits(sample_pridb):
    hits = sample_pridb.read_hits()

    assert len(hits) == len(HITS_EXPECTED)
    assert hits.index.name == "set_id"
    assert hits.index.dtype == int64
    assert dict(hits.dtypes) == {
        "time": float64,
        "channel": Int64Dtype(),
        "param_id": Int64Dtype(),
        "threshold": float64,
        "amplitude": float64,
        "rise_time": float64,
        "cascade_counts": Int64Dtype(),
        "cascade_energy": float64,
        "cascade_hits": Int64Dtype(),
        "cascade_signal_strength": float64,
        "counts": Int64Dtype(),
        "duration": float64,
        "energy": float64,
        "rms": float64,
        "signal_strength": float64,
        "trai": Int64Dtype(),
    }


def test_iread_parametric(sample_pridb):
    records = list(sample_pridb.iread_parametric())
    assert len(records) == len(PARAMETRIC_EXPECTED)

    for record, record_expected in zip(records, PARAMETRIC_EXPECTED):
        assert record.set_id == record_expected.set_id
        assert record.time == pytest.approx(record_expected.time)
        assert record.param_id == record_expected.param_id
        assert record.pctd == record_expected.pctd
        assert record.pcta == record_expected.pcta
        assert record.pa0 == record_expected.pa0
        assert record.pa1 == record_expected.pa1
        assert record.pa2 == record_expected.pa2
        assert record.pa3 == record_expected.pa3
        assert record.pa4 == record_expected.pa4
        assert record.pa5 == record_expected.pa5
        assert record.pa6 == record_expected.pa6
        assert record.pa7 == record_expected.pa7


def test_iread_parametric_query_filter(sample_pridb):
    records = list(sample_pridb.iread_parametric(query_filter="SetID > 10"))
    assert len(records) == 4


def test_read_parametric(sample_pridb):
    df = sample_pridb.read_parametric()

    assert len(df) == len(PARAMETRIC_EXPECTED)
    assert df.index.name == "set_id"
    assert df.index.dtype == int64
    assert dict(df.dtypes) == {
        "param_id": Int64Dtype(),
        "time": float64,
        "pctd": Int64Dtype(),
        "pcta": Int64Dtype(),
    }


def test_read(sample_pridb):
    df = sample_pridb.read()

    assert df.index.name == "set_id"
    assert df.index.dtype == int64
    assert dict(df.dtypes) == {
        "set_type": int64,
        "time": float64,
        "channel": Int64Dtype(),
        "param_id": Int64Dtype(),
        "threshold": float64,
        "amplitude": float64,
        "rise_time": float64,
        "cascade_counts": Int64Dtype(),
        "cascade_energy": float64,
        "cascade_hits": Int64Dtype(),
        "cascade_signal_strength": float64,
        "counts": Int64Dtype(),
        "duration": float64,
        "energy": float64,
        "rms": float64,
        "signal_strength": float64,
        "trai": Int64Dtype(),
        "pctd": Int64Dtype(),
        "pcta": Int64Dtype(),
    }


def test_listen(sample_pridb):
    assert len(list(sample_pridb.listen())) == 0
    assert len(list(sample_pridb.listen(existing=True))) == 18

    def records_by_type(type_):
        return list(filter(lambda r: isinstance(r, type_), sample_pridb.listen(existing=True)))

    assert records_by_type(HitRecord) == list(sample_pridb.iread_hits())
    assert records_by_type(MarkerRecord) == list(sample_pridb.iread_markers())
    assert records_by_type(ParametricRecord) == list(sample_pridb.iread_parametric())
    assert records_by_type(StatusRecord) == list(sample_pridb.iread_status())


def test_write_readonly(sample_pridb):
    with pytest.raises(ValueError):
        sample_pridb.write_marker(MarkerRecord(set_id=1, time=0, set_type=4, number=1, data="Test"))


def test_write_hit(fresh_pridb):
    new_hit = HitRecord(
        time=5,
        channel=1,
        param_id=1,
        threshold=111,
        amplitude=22222,
        rise_time=111,
        duration=11111,
        energy=12345678,
        signal_strength=20000,
        rms=5,
        counts=1987,
    )

    assert fresh_pridb.write_hit(new_hit) == 1
    assert fresh_pridb.rows() == 1

    hit_read = next(iter(fresh_pridb.iread_hits()))
    assert hit_read.set_id == 1  # first data set
    assert hit_read.time == new_hit.time
    assert hit_read.channel == new_hit.channel
    assert hit_read.param_id == new_hit.param_id
    assert hit_read.threshold == new_hit.threshold
    assert hit_read.amplitude == new_hit.amplitude
    assert hit_read.rise_time == new_hit.rise_time
    assert hit_read.duration == new_hit.duration
    assert hit_read.energy == new_hit.energy
    assert hit_read.signal_strength == new_hit.signal_strength
    assert hit_read.rms == pytest.approx(new_hit.rms)
    assert hit_read.counts == new_hit.counts
    assert hit_read.trai == new_hit.trai
    assert hit_read.cascade_hits == new_hit.cascade_hits
    assert hit_read.cascade_counts == new_hit.cascade_counts
    assert hit_read.cascade_energy == new_hit.cascade_energy
    assert hit_read.cascade_signal_strength == new_hit.cascade_signal_strength


def test_write_marker(fresh_pridb):
    new_marker = MarkerRecord(
        time=11.11,
        set_type=4,
        number=1,
        data="Test label",
    )

    assert fresh_pridb.write_marker(new_marker) == 1
    assert fresh_pridb.rows() == 1

    marker_read = next(iter(fresh_pridb.iread_markers()))
    assert marker_read.set_id == 1  # first data set
    assert marker_read.time == new_marker.time
    assert marker_read.set_type == new_marker.set_type
    assert marker_read.number == new_marker.number
    assert marker_read.data == new_marker.data


def test_write_status(fresh_pridb):
    new_status = StatusRecord(
        time=11.11,
        channel=1,
        param_id=1,
        threshold=100,
        energy=111,
        signal_strength=222,
        rms=5,
    )

    assert fresh_pridb.write_status(new_status) == 1
    assert fresh_pridb.rows() == 1

    status_read = next(iter(fresh_pridb.iread_status()))
    assert status_read.set_id == 1  # first data set
    assert status_read.time == new_status.time
    assert status_read.channel == new_status.channel
    assert status_read.param_id == new_status.param_id
    assert status_read.threshold == new_status.threshold
    assert status_read.energy == new_status.energy
    assert status_read.signal_strength == new_status.signal_strength
    assert status_read.rms == pytest.approx(new_status.rms)


def test_write_parametric(fresh_pridb):
    new_parametric = ParametricRecord(
        time=11.11,
        param_id=1,
        pctd=11,
        pcta=22,
    )

    assert fresh_pridb.write_parametric(new_parametric) == 1
    assert fresh_pridb.rows() == 1

    parametric_read = next(iter(fresh_pridb.iread_parametric()))
    assert parametric_read.set_id == 1  # first data set
    # assert parametric_read.status == new_parametric.status
    assert parametric_read.time == new_parametric.time
    assert parametric_read.param_id == new_parametric.param_id
    assert parametric_read.pctd == new_parametric.pctd
    assert parametric_read.pcta == new_parametric.pcta


def test_check_monotonic_time(fresh_pridb):
    def generate_marker(time: float):
        return MarkerRecord(
            time=time,
            set_type=4,
            number=1,
            data="Test label",
        )

    fresh_pridb.write_marker(generate_marker(1.0))
    fresh_pridb.write_marker(generate_marker(1.0))
    with pytest.raises(ValueError):
        fresh_pridb.write_marker(generate_marker(0.9))


def test_read_empty_pridb(fresh_pridb):
    # dtype conversion might fail because of missing columns
    df = fresh_pridb.read()
    assert len(df) == 0
    assert list(df.columns) == []
