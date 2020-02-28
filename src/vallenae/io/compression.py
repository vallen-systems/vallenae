import io

import numpy as np
from numba import njit

try:
    import soundfile as sf
    _FLAC_CODEC = True
except OSError:
    _FLAC_CODEC = False


_II16_MIN = np.iinfo(np.int16).min
_II16_MAX = np.iinfo(np.int16).max


def _check_flac_codec():
    if not _FLAC_CODEC:
        raise ValueError("FLAC library not found. Please install libsndfile.")


@njit
def _convert_to_int16(arr: np.ndarray):
    result = np.empty_like(arr, dtype=np.int16)
    for i, value in enumerate(arr):
        # clip to range of int16
        value = min(value, _II16_MAX)
        value = max(value, _II16_MIN)
        # round to next integer
        result[i] = round(value)
    return result


def decode_data_blob(
    data_blob: bytes, data_format: int, factor_millivolts: float
) -> np.ndarray:
    """
    Decodes (compressed) 16-bit ADC values from BLOB to array of voltage values.

    Args:
        data_blob: Blob from tradb
        data_format:
            - 0: uncompressed
            - 2: FLAC compression
        factor_millivolts: Factor from int16 representation to millivolts.
            Stored in tradb -> tr_params as 'TR_mV'

    Returns:
        Array of voltage values
    """
    if data_format == 0:  # uncompressed
        data = np.frombuffer(data_blob, dtype=np.int16)
        factor = 1e-3 * factor_millivolts
        return np.multiply(data, factor, dtype=np.float32)
    if data_format == 2:  # flac
        _check_flac_codec()
        data, _ = sf.read(io.BytesIO(data_blob), dtype=np.float32)
        factor_libsoundfile = 2 ** 15  # libsoundfile normalizes to +-1
        factor = 1e-3 * factor_millivolts * factor_libsoundfile
        return np.multiply(data, factor, dtype=np.float32)
    raise ValueError("Data format not supported")


def encode_data_blob(
    data: np.ndarray, data_format: int, factor_millivolts: float
) -> bytes:
    """
    Encodes array of voltage values to BLOB of 16-bit ADC values
    for memory-efficient storage.

    Args:
        data: Array with voltage values
        data_format:
            - 0: uncompressed
            - 2: FLAC compression
        factor_millivolts: Factor from int16 representation to millivolts.
            Stored in tradb -> tr_params as 'TR_mV'

    Returns:
        Data blob
    """
    data = data * 1e3 / factor_millivolts
    data_int16 = _convert_to_int16(data)
    if data_format == 0:  # uncompressed
        return data_int16.tobytes()
    if data_format == 2:  # flac
        _check_flac_codec()
        buffer = io.BytesIO()
        sf.write(buffer, data_int16, 1, format="FLAC")  # samplerate = 1
        return buffer.getvalue()
    raise ValueError("Data format not supported")
