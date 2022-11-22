import io

import numpy as np

try:
    import soundfile as sf
    _FLAC_CODEC = True
except OSError:
    _FLAC_CODEC = False


def _check_flac_codec():
    if not _FLAC_CODEC:
        raise ValueError("FLAC library not found. Please install libsndfile.")


def decode_data_blob(
    data_blob: bytes, data_format: int, factor_millivolts: float, *, raw: bool = False
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
        raw: Return data as ADC values (`np.int16`), `factor_millivolts` will be ignored

    Returns:
        Array of voltage values or ADC values if `raw` is `True`
    """
    def get_data_int16():
        if data_format == 0:  # uncompressed
            return np.frombuffer(data_blob, dtype=np.int16)
        if data_format == 2:  # flac
            _check_flac_codec()
            return sf.read(io.BytesIO(data_blob), dtype=np.int16)[0]
        raise ValueError("Data format not supported")

    data_int16 = get_data_int16()
    if raw:
        return data_int16
    return np.multiply(data_int16, 1e-3 * factor_millivolts, dtype=np.float32)


def encode_data_blob(
    data: np.ndarray, data_format: int, factor_millivolts: float, *, raw: bool = False
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
        raw: Provide `data` as ADC values (int16), `factor_millivolts` will be ignored

    Returns:
        Data blob
    """
    ii16_min = np.iinfo(np.int16).min
    ii16_max = np.iinfo(np.int16).max

    def get_data_int16():
        if raw:
            return data.astype(np.int16, casting="safe", copy=False)  # only safe casts!
        temp = np.empty_like(data, dtype=np.float32)
        np.multiply(data, 1e3 / factor_millivolts, out=temp)
        # faster than np.clip(temp, a_min=ii16_min, a_max=ii16_max, out=temp)
        np.minimum(temp, ii16_max, out=temp)
        np.maximum(temp, ii16_min, out=temp)
        # faster than np.rint(temp, out=temp)
        np.floor(temp + 0.5, out=temp)
        return temp.astype(np.int16)

    data_int16 = get_data_int16()
    if data_format == 0:  # uncompressed
        return data_int16.tobytes()
    if data_format == 2:  # flac
        _check_flac_codec()
        buffer = io.BytesIO()
        sf.write(buffer, data_int16, samplerate=1, format="FLAC")
        return buffer.getvalue()
    raise ValueError("Data format not supported")
