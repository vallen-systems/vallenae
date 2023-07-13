import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from vallenae.io import decode_data_blob, encode_data_blob


@pytest.mark.parametrize(
    "dtype",
    [np.int8, np.uint8, np.int16],
)
def test_encode_datatype_raw_allow(dtype):
    encode_data_blob(np.zeros(0, dtype=dtype), 0, 1, raw=True)


@pytest.mark.parametrize(
    "dtype",
    [np.uint16, np.int32, np.int64, np.float32, np.float64, np.complex64],
)
def test_encode_datatype_raw_deny(dtype):
    with pytest.raises(TypeError):
        encode_data_blob(np.zeros(0, dtype=dtype), 0, 1, raw=True)


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("data_format", [0, 2])
def test_encode_decode_i16_to_i16(data_format: int, raw: bool):
    # generate range of all possible values
    ii16 = np.iinfo(np.int16)
    data_int16 = np.arange(ii16.min, ii16.max, dtype=np.int16)
    data = data_int16 if raw else data_int16.astype(np.float32)
    factor_millivolts = 1e3

    # encode, decode
    data_blob = encode_data_blob(data, data_format, factor_millivolts, raw=raw)
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts, raw=raw)

    # compare input <-> decoded
    assert_array_equal(data_decoded, data)


@pytest.mark.parametrize("factor_millivolts", [1, 0.1, 0.01, 0.001])
@pytest.mark.parametrize("data_format", [0, 2])
def test_encode_decode_f32_to_f32(data_format: int, factor_millivolts: float):
    # calculate min/max amplitude to prevent clipping float32 -> int16
    ii16 = np.iinfo(np.int16)
    amin = ii16.min * 1e-3 * factor_millivolts
    amax = ii16.max * 1e-3 * factor_millivolts
    # generate data with floats in possible range
    data = np.linspace(amin, amax, 2**16, endpoint=True, dtype=np.float32)

    # encode, decode
    data_blob = encode_data_blob(data, data_format, factor_millivolts)
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts)

    # compare input <-> decoded
    assert len(data_decoded) == len(data)

    adc_step = amax * (2**-15)
    assert_allclose(data_decoded, data, atol=adc_step, rtol=0)  # why so high tolerance necessary?


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("factor_millivolts", [1, 0.001])
@pytest.mark.parametrize("data_format", [0, 2])
def test_decode_encode_blob_to_blob(data_format: int, factor_millivolts: float, raw: bool):
    def generate_random_blob():
        ii16 = np.iinfo(np.int16)
        data = np.random.randint(low=ii16.min, high=ii16.max, size=1024, dtype=np.int16)
        return encode_data_blob(data, data_format, factor_millivolts, raw=True)

    data_blob = generate_random_blob()

    # decode, encode
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts, raw=raw)
    data_blob_2 = encode_data_blob(data_decoded, data_format, factor_millivolts, raw=raw)

    assert data_blob == data_blob_2
