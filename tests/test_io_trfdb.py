from pathlib import Path

import pytest
import vallenae as vae
from vallenae.io import FeatureRecord
from vallenae.io._sql import read_sql_generator

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRFDB = STEEL_PLATE_DIR / "sample.trfdb"

TRFS_EXPECTED = [
    FeatureRecord(
        trai=1,
        features={
            "FFT_CoG": 147.705078125,
            "FFT_FoM": 134.27734375,
            "PA": 46.4838638305664,
            "RT": 49.4000015258789,
            "Dur": 19671.400390625,
            "CTP": 11,
            "FI": 222.672058105469,
            "FR": 110.18244934082,
        }
    ),
    FeatureRecord(
        trai=2,
        features={
            "FFT_CoG": 144.04296875,
            "FFT_FoM": 139.16015625,
            "PA": 59.450511932373,
            "RT": 192.0,
            "Dur": 20575.599609375,
            "CTP": 35,
            "FI": 182.29167175293,
            "FR": 98.0199813842773,
        }
    ),
    FeatureRecord(
        trai=3,
        features={
            "FFT_CoG": 155.029296875,
            "FFT_FoM": 164.794921875,
            "PA": 33.9952087402344,
            "RT": 354.399993896484,
            "Dur": 19130.599609375,
            "CTP": 55,
            "FI": 155.191879272461,
            "FR": 95.4932327270508,
        }
    ),
    FeatureRecord(
        trai=4,
        features={
            "FFT_CoG": 159.912109375,
            "FFT_FoM": 139.16015625,
            "PA": 29.1148281097412,
            "RT": 160.199996948242,
            "Dur": 19266.0,
            "CTP": 29,
            "FI": 181.023727416992,
            "FR": 101.906227111816,
        }
    ),
]


@pytest.fixture(name="sample_trfdb")
def fixture_sample_trfdb() -> vae.io.TrfDatabase:
    with vae.io.TrfDatabase(SAMPLE_TRFDB) as trfdb:
        yield trfdb


@pytest.fixture(name="fresh_trfdb")
def fixture_fresh_trfdb(tmp_path) -> vae.io.TrfDatabase:
    filename = tmp_path / "test.trfdb"
    with vae.io.TrfDatabase(filename, mode="rwc") as trfdb:
        yield trfdb


def test_init():
    trfdb = vae.io.TrfDatabase(SAMPLE_TRFDB)
    trfdb.close()


def test_create(tmp_path):
    filename = tmp_path / "empty.trfdb"
    vae.io.TrfDatabase.create(filename)
    with vae.io.TrfDatabase(filename) as trfdb:
        assert trfdb.tables() == {
            "trf_data", "trf_fieldinfo", "trf_globalinfo",
        }


def test_iread(sample_trfdb):
    trfs = list(sample_trfdb.iread())

    assert len(trfs) == len(TRFS_EXPECTED)

    for trf, trf_expected in zip(trfs, TRFS_EXPECTED):
        assert trf.trai == trf_expected.trai

        for (key, value), (key_expected, value_expected) in zip(
            trf.features.items(),
            trf_expected.features.items()
        ):
            assert key == key_expected
            assert value == pytest.approx(value_expected)


def test_read(sample_trfdb):
    df = sample_trfdb.read()

    assert set(df.columns) == {"FR", "Dur", "FFT_CoG", "CTP", "RT", "FFT_FoM", "FI", "PA"}
    assert len(df) == len(TRFS_EXPECTED)
    assert df.index.name == "trai"


def test_listen(sample_trfdb):
    assert len(list(sample_trfdb.listen())) == 0

    existing_records_sorted = sorted(sample_trfdb.listen(existing=True), key=lambda r: r.trai)
    assert existing_records_sorted == list(sample_trfdb.iread())


def test_write(fresh_trfdb):
    def get_by_trai(trai):
        gen = read_sql_generator(
            fresh_trfdb.connection(),
            f"SELECT * FROM trf_data WHERE TRAI == {trai}",
        )
        return next(iter(gen))

    # first insert
    assert fresh_trfdb.rows() == 0
    fresh_trfdb.write(FeatureRecord(trai=0, features={"Test": 11.11}))
    assert fresh_trfdb.rows() == 1
    assert get_by_trai(0)["Test"] == 11.11

    # update
    fresh_trfdb.write(FeatureRecord(trai=0, features={"Test": 22.22}))
    assert get_by_trai(0)["Test"] == 22.22

    # add new column
    fresh_trfdb.write(FeatureRecord(trai=1, features={"New": -33.33}))
    assert get_by_trai(0)["New"] is None
    assert get_by_trai(1)["New"] == -33.33
