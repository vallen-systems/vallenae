import pickle
import sqlite3
from pathlib import Path

import pytest
from vallenae.io import PriDatabase
from vallenae.io._database import Database

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
PRIDB_FILE_PATH = STEEL_PLATE_DIR / "sample.pridb"
TRADB_FILE_PATH = STEEL_PLATE_DIR / "sample.tradb"


@pytest.fixture(name="sample_pridb")
def fixture_sample_pridb():
    database = Database(PRIDB_FILE_PATH, table_prefix="ae")
    yield database
    database.close()


@pytest.fixture(name="sample_tradb")
def fixture_sample_tradb():
    database = Database(TRADB_FILE_PATH, table_prefix="tr")
    yield database
    database.close()


@pytest.fixture(name="empty_pridb")
def fixture_empty_pridb(tmp_path):
    filename = tmp_path / "test.pridb"
    PriDatabase.create(filename)
    with Database(filename, mode="rw", table_prefix="ae") as db:
        yield db


def test_init():
    # try open not existing database
    with pytest.raises(sqlite3.OperationalError):
        Database("file_does_not_exist.database", table_prefix="ae")

    # open existing database
    database = Database(PRIDB_FILE_PATH, table_prefix="ae")
    assert database.connected
    database.close()
    assert not database.connected
    database.close()  # double close should not cause an exception

    # require file extension
    with pytest.raises(ValueError):
        Database(PRIDB_FILE_PATH, table_prefix="ae", required_file_ext=".nonsense")


def test_context():
    with Database(PRIDB_FILE_PATH, table_prefix="ae") as database:
        # check if connection is opened with __enter__
        assert database.connected
    # check if connection is closed with __exit__
    assert not database.connected


def test_main_table_not_existing():
    # exception is thrown, if main table doesn"t exist
    with pytest.raises(ValueError):
        Database(PRIDB_FILE_PATH, table_prefix="tr")


def test_create():
    with pytest.raises(NotImplementedError):
        Database.create("test.db")

    with pytest.raises(NotImplementedError):
        Database("test.db", mode="rwc", table_prefix="")


def test_tables_pridb(sample_pridb):
    assert sample_pridb._table_main == "ae_data"
    assert sample_pridb.tables() == {
        "ae_data",
        "acq_setup",
        "ae_markers",
        "ae_globalinfo",
        "ae_fieldinfo",
        "ae_params",
        "data_integrity"
    }


def test_tables_tradb(sample_tradb):
    assert sample_tradb._table_main == "tr_data"
    assert sample_tradb.tables() == {
        "tr_data",
        "tr_fieldinfo",
        "tr_globalinfo",
        "tr_params",
    }


def test_rows(sample_pridb):
    assert sample_pridb.rows() == 18


def test_columns(sample_pridb):
    assert sample_pridb.columns() == (
        "SetID", "SetType", "Time", "Chan", "Status", "ParamID",
        "Thr", "Amp", "RiseT", "Dur", "Eny", "SS", "RMS", "Counts",
        "TRAI", "CCnt", "CEny", "CSS", "CHits", "PCTD", "PCTA",
    )


def test_check_connection(sample_pridb):
    sample_pridb.close()

    with pytest.raises(RuntimeError):
        sample_pridb.rows()

    with pytest.raises(RuntimeError):
        sample_pridb.columns()


def test_globalinfo(sample_pridb):
    info = sample_pridb.globalinfo()

    assert info["Version"] == 1
    assert isinstance(info["Version"], int)
    assert info["FileStatus"] == 0
    assert isinstance(info["FileStatus"], int)
    assert info["TimeBase"] == int(1e7)
    assert isinstance(info["TimeBase"], int)
    assert info["WriterID"] == "-"
    assert isinstance(info["WriterID"], str)
    assert info["FileID"] == "{60854854-6E8D-472F-AE70-7ED9DE68BA38}"
    assert isinstance(info["FileID"], str)
    assert info["ValidSets"] == 18
    assert isinstance(info["ValidSets"], int)
    assert info["TRAI"] == 4
    assert isinstance(info["TRAI"], int)


def test_file_status(sample_pridb):
    assert sample_pridb._file_status() == 0


def test_main_index_range(sample_pridb):
    assert sample_pridb._main_index_range() == (1, 18)


def test_parameter(sample_pridb):
    assert sample_pridb._parameter(1) == {
        "SetupID": 1,
        "Chan": 0,
        "ADC_µV": 0.0,
        "ADC_TE": 0.0,
        "ADC_SS": 0.0
    }

    assert sample_pridb._parameter(2) == pytest.approx({
        "SetupID": 1,
        "Chan": 1,
        "ADC_µV": 1.52226441093467,
        "ADC_TE": 9.26915433618267e-5,
        "ADC_SS": 0.000304452859014046
    })

    with pytest.raises(ValueError):
        sample_pridb._parameter(0)
    with pytest.raises(ValueError):
        sample_pridb._parameter(6)


def test_fieldinfo_tradb(sample_tradb):
    result = sample_tradb.fieldinfo()

    assert list(result.keys()) == ["Time", "Thr", "SampleRate", "Data"]

    assert result["Time"] == {"Unit": "[s]", "Parameter": None}
    assert result["Thr"] == {"Unit": "[µV]", "Parameter": "ADC_µV"}
    assert result["SampleRate"] == {"Unit": "[Hz]", "Parameter": None}
    assert result["Data"] == {"Unit": None, "Parameter": "TR_mV"}


def test_fieldinfo_mixed_types(sample_pridb):
    result = sample_pridb.fieldinfo()

    assert result["Dur"] == {
        "Unit": "[µs]",
        "SetTypes": 4,
        "Parameter": None,
        "Factor": 0.1,
    }


def test_write_fieldinfo(empty_pridb):
    def count_rows(field: str):
        con = empty_pridb.connection()
        cur = con.execute(f"SELECT COUNT(field) FROM ae_fieldinfo WHERE field == '{field}'")
        return cur.fetchone()[0]

    # update
    empty_pridb.write_fieldinfo("Time", {"Unit": "[hours]"})
    assert empty_pridb.fieldinfo()["Time"]["Unit"] == "[hours]"
    assert count_rows("Time") == 1

    # write new column
    empty_pridb.write_fieldinfo("Time", {"XYZ": 11})
    assert empty_pridb.fieldinfo()["Time"]["XYZ"] == 11
    assert count_rows("Time") == 1

    # try write field, that doesn't correspond to column in data table
    with pytest.raises(ValueError):
        empty_pridb.write_fieldinfo("NotAColumn", {"Unit": "[Hz]"})


def test_pickle(sample_pridb):
    pkl = pickle.dumps(sample_pridb)
    pridb_unpickled = pickle.loads(pkl)

    # run random queries
    assert pridb_unpickled.tables() == sample_pridb.tables()
    assert pridb_unpickled.rows() == sample_pridb.rows()
    assert pridb_unpickled.columns() == sample_pridb.columns()
