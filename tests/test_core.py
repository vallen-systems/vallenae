from .context import vae
import numpy as np
import os
import pandas as pd

THIS_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
STEEL_PLATE_DIR = os.path.join(THIS_FILE_PATH, '../examples/steel_plate')
PRI_FILE_PATH = os.path.join(STEEL_PLATE_DIR, 'sample.pridb')
FLAC_TRA_FILE_PATH = os.path.join(STEEL_PLATE_DIR, 'sample.tradb')
PLAIN_TRA_FILE_PATH = os.path.join(STEEL_PLATE_DIR, 'sample_plain.tradb')


def test_read_pri():

    pri_frame = vae.read_pri(PRI_FILE_PATH, 1, 18)
    assert type(pri_frame) is pd.DataFrame
    val_set = {'SetType', 'Time', 'Chan', 'Status', 'Thr', 'Amp', 'RiseT',
               'Dur', 'Eny', 'SS', 'RMS', 'Counts', 'TRAI', 'CCnt', 'CEny',
               'CSS', 'CHits', 'PCTD', 'PCTA'}
    check_set = set(pri_frame.columns)
    assert val_set == check_set
    assert pri_frame.shape == (18, 19)  # 18 rows, 19 columns


def test_read_tra():

    tra_frame = vae.read_tra(PLAIN_TRA_FILE_PATH, 1, 18)
    assert type(tra_frame) is pd.DataFrame
    val_set = {'SetID', 'Time', 'Status', 'Chan', 'Pretrigger', 'Thr',
               'SampleRate', 'Samples', 'DataFormat', 'TR_mV', 'Data'}
    check_set = set(tra_frame.columns)
    assert val_set == check_set
    assert tra_frame.shape == (4, 11)  # 4 rows, 11 columns


def test_extract_wave():

    huge = int(1e6)
    tra_frame_flac = vae.read_tra(FLAC_TRA_FILE_PATH, 1, huge)
    tra_frame_plain = vae.read_tra(PLAIN_TRA_FILE_PATH, 1, huge)
    assert tra_frame_flac.shape == tra_frame_plain.shape
    nb_tras, _ = tra_frame_flac.shape

    # It shouldn't matter whether we extract a compressed or a plain db:
    for idx in range(1, nb_tras+1):
        plain_vals, plain_ts = vae.extract_wave(tra_frame_plain, idx)
        flac_vals, flac_ts = vae.extract_wave(tra_frame_flac, idx)
        assert np.array_equal(flac_vals, plain_vals)
        assert np.array_equal(flac_ts, plain_ts)


def test_read_labels():

    labels = ['',
              '10:52 Resume',
              '2019-09-20 10:54:52',
              'TimeZone: +02:00 (W. Europe Standard Time)',
              '10:56 Suspend']
    markers = vae.read_labels(PRI_FILE_PATH)
    assert list(markers['Data']) == labels
