from __future__ import print_function, unicode_literals, division

import array as arr
import contextlib as ctxlib
import io
import numpy as np
import os
import pandas as pd
import re
import soundfile as sf
import sqlite3
from typing import Tuple, Union
from ._version import __version_tpl__

TBL_NAME_PATTERN = re.compile("^([A-Z]|[a-z]|_)+$")
FLAC_SPECIFIER = 2
PLAIN_SPECIFIER = 0

_version = __version_tpl__


def read_pri(abs_file_name: str,
             from_: int,
             to_: int)\
        -> pd.DataFrame:
    """
    Runs the following query on the pri-db file referenced by abs_file_name:
       SELECT * FROM view_tr_data
       WHERE SetID BETWEEN from_ AND to_

    :param abs_file_name: Absolute file name of the transient database. E.g.
        "C:\ae_test.pridb"
    :param from_: Start SetID
    :param to_: End SetID
    :returns: A pandas dataframe containing all available columns.
    """
    data_frame = _read_db(abs_file_name, 'view_ae_data', 'SetID', from_, to_)
    return data_frame


def read_tra(abs_file_name: str,
             from_: int,
             to_: int)\
        -> pd.DataFrame:
    """
    Runs the following query on the tra-db file referenced by abs_file_name:
       SELECT * FROM view_tr_data
       WHERE SetID BETWEEN from_ AND to_

    :param abs_file_name: Absolute file name of the transient database. E.g.
        "C:\ae_test.tradb"
    :param from_: Start TRAI
    :param to_: End TRAI
    :returns: A pandas dataframe containing all available columns.
    """
    data_frame = _read_db(abs_file_name, 'view_tr_data', 'TRAI', from_, to_)
    return data_frame


def extract_wave(pd_tra_frame: pd.DataFrame,
                 tra_idx: int,
                 do_convert2v: bool = True,
                 do_create_time_vector: bool = True)\
        -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts a single waveform according to the given index.

    :param pd_tra_frame: Transient data given as a pandas dataframe object.
    :param tra_idx: Transient index of the waveform to extract.
    :param do_convert2v: For performance reasons. Should we convert to V?
    :param do_create_time_vector: For performance reasons. Should we create a
        suitable time vector for the x-axis, i.e. for plotting?
    :returns: (scaled values in V, time vector in seconds)
    """
    data_format = pd_tra_frame['DataFormat'][tra_idx]

    if data_format not in {PLAIN_SPECIFIER, FLAC_SPECIFIER}:
        raise TypeError("Unknown BLOB format. data_format = " +
                        str(data_format))

    do_use_flac = data_format == FLAC_SPECIFIER

    return _extract_wave(pd_tra_frame,
                         tra_idx,
                         do_use_flac,
                         do_convert2v,
                         do_create_time_vector)


def read_labels(abs_file_name: str)\
        -> pd.DataFrame:
    """
    Read all the labels of the database file into a pandas dataframe.

    :param abs_file_name: Absolute path to the sqlite3 database file.
    :returns: The view_ae_markers table as pandas dataframe.
    """
    query = 'SELECT SetID, Number, Data ' +\
            'FROM view_ae_markers'
    data_frame = None
    if os.path.exists(abs_file_name):
        with ctxlib.closing(sqlite3.connect(abs_file_name)) as db_conn:
            data_frame = pd.read_sql_query(query, db_conn)
    if data_frame is not None:
        data_frame = data_frame.set_index('SetID')
    return data_frame


def _read_db(abs_file_name: str,
             tbl_name: str,
             indx: str,
             from_: int,
             to_: int)\
        -> pd.DataFrame:
    """
    Internal helper function to read sqlite3 databases into a pandas dataframe.
        SELECT * FROM tbl_name WHERE SetID BETWEEN from_ AND to_

    :param abs_file_name: Absolute path name of the database file. E.g.
        "C:\\sample.sqlite3" or "C:\\ae_test.pridb"
    :param tbl_name: The table to read from, e.g. view_ae_data.
    :param indx: Using a conversion to pd.DataFrameThe we want to set an index.
    :param from_: Start SetID
    :param to_: End SetID
    :returns: A pandas dataframe object.
    """
    # Table names can not be bound; at least we try to prevent
    # sql-injection in some way:
    if not TBL_NAME_PATTERN.match(tbl_name):
        raise Exception('Illegal table name ' + tbl_name + '\n' +
                        'Should consist just of letters and underscores.')
    query = ('SELECT * FROM ' + tbl_name +
             ' WHERE SetID >= ? AND SetID <= ?')
    binding_params = (from_, to_)
    data_frame = None
    if os.path.exists(abs_file_name):
        with ctxlib.closing(sqlite3.connect(abs_file_name)) as db_conn:
            data_frame = pd.read_sql_query(query, db_conn,
                                           params=binding_params)
    if data_frame is not None:
        data_frame = data_frame.set_index(indx)
    return data_frame


def _get_sr_pt_smpls_2mv(pd_tra_frame: pd.DataFrame,
                         tra_idx: int)\
        -> Tuple[int, int, int, float]:
    """
    Internal helper function to extract the sample rate, the number of
    pre-trigger samples, the overall number of samples and the ADC to mV
    conversion factor - given a dataframe and an index of the referenced
    waveform.

    :param pd_tra_frame: The pandas dataframe to read from.
    :param tra_idx: The index of the waveform of interest.
    :returns (sample_rate, nb_pretrigs, nb_samples, raw2mv_factor):
    """
    sample_rate = int(pd_tra_frame['SampleRate'][tra_idx])
    nb_pretrigs = int(pd_tra_frame['Pretrigger'][tra_idx])
    nb_samples = int(pd_tra_frame['Samples'][tra_idx])
    raw2mv_factor = float(pd_tra_frame['TR_mV'][tra_idx])

    return sample_rate, nb_pretrigs, nb_samples, raw2mv_factor


def _create_time_vector(nb_pretrigs: int,
                        nb_samples: int,
                        sample_rate: int)\
        -> np.ndarray:
    """
    Internal helper function to create a time base vector.

    :param nb_pretrigs: Number of pretrigger samples.
    :param nb_samples: Overall number of samples.
    :param sample_rate:
    :return A time base vector that could be used to generate appropriate
        plots (x-axis).
    """
    raw_time_vec = np.arange(-nb_pretrigs, nb_samples - nb_pretrigs)
    scaled_time_vec = np.multiply(raw_time_vec, 1.0/sample_rate)

    return scaled_time_vec


def _extract_wave(pd_tra_frame: pd.DataFrame,
                  tra_idx: int,
                  do_use_flac: bool,
                  do_convert2v: bool = True,
                  do_create_time_vector: bool = True)\
        -> Union[Tuple[np.ndarray, np.ndarray], np.ndarray]:
    """
    Helper function to extract little endian 16-bit adc values from a BLOB.
    Is capable of handling FLAC format.
    """
    sr, nb_pretrigs, nb_smpls, to_mv_factor = \
        _get_sr_pt_smpls_2mv(pd_tra_frame, tra_idx)

    blob = pd_tra_frame['Data'][tra_idx]

    if do_use_flac:
        result, _ = sf.read(io.BytesIO(blob))
        # the soundfile lib normalizes the adc values to +-1, that's why
        # we need this:
        to_mv_factor = to_mv_factor * 2**15
    else:
        result = np.array(arr.array('h', bytes(blob)))

    if do_convert2v:
        result = np.multiply(1e-3*to_mv_factor, result)

    if not do_create_time_vector:
        return result
    else:
        return result, _create_time_vector(nb_pretrigs=nb_pretrigs,
                                           nb_samples=nb_smpls,
                                           sample_rate=sr)
