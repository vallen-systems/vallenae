import os
from pathlib import Path
import pytest

import vallenae as vae
from vallenae.io import FeatureRecord, create_empty_trfdb

STEEL_PLATE_DIR = Path(__file__).resolve().parent / "../examples/steel_plate"
SAMPLE_TRFDB = STEEL_PLATE_DIR / "sample.trfdb"

FEATURES_EXPECTED = [
    # TraRecord(
    #     time=3.9927747, channel=2, param_id=3, pretrigger=500, threshold=100.469451121688,
    #     samplerate=5000000, samples=103488, data_format=2, data=np.empty(0), trai=2
    # ),
    # TraRecord(
    #     time=3.992771, channel=3, param_id=4, pretrigger=500, threshold=100.469451121688,
    #     samplerate=5000000, samples=98960, data_format=2, data=np.empty(0), trai=1
    # ),
    # TraRecord(
    #     time=3.9928129, channel=4, param_id=5, pretrigger=500, threshold=100.469451121688,
    #     samplerate=5000000, samples=96256, data_format=2, data=np.empty(0), trai=3
    # ),
    # TraRecord(
    #     time=3.9928143, channel=1, param_id=2, pretrigger=500, threshold=100.469451121688,
    #     samplerate=5000000, samples=96944, data_format=2, data=np.empty(0), trai=4
    # ),
]


@pytest.fixture(name="sample_trfdb")
def fixture_sample_trfdb() -> vae.io.TrfDatabase:
    with vae.io.TrfDatabase(SAMPLE_TRFDB) as trfdb:
        yield trfdb


@pytest.fixture(name="fresh_trfdb")
def fixture_fresh_trfdb() -> vae.io.TrfDatabase:
    filename = "test.trfdb"
    create_empty_trfdb(filename)
    trfdb = vae.io.TrfDatabase(filename, readonly=False)
    yield trfdb
    trfdb.close()
    os.remove(filename)


def test_read(sample_trfdb):
    df = sample_trfdb.read()
    assert set(df.columns) == {"FR", "Dur", "FFT_CoG", "CTP", "RT", "FFT_FoM", "FI", "PA"}
    print(sample_trfdb.read(trai=(1, 2)))
    print(sample_trfdb.columns())
    # assert False

# def test_iread(sample_trfdb):
#     for x in sample_trfdb.iread():
#         print(x)
#     assert False

def test_write(fresh_trfdb):
    fresh_trfdb.write(FeatureRecord(trai=0, features={"Test": 11}))
    fresh_trfdb.write(FeatureRecord(trai=0, features={"Test": 11}))
    assert False