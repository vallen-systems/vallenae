import pytest
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal

from vallenae.io import decode_data_blob, encode_data_blob


@pytest.mark.parametrize("data_format", (0, 2))
def test_encode_decode_i16_to_i16(data_format: int):
    ii16 = np.iinfo(np.int16)
    # generate range of all possible values
    data = np.arange(ii16.min, ii16.max, dtype=np.int16)
    factor_millivolts = 1e3

    # encode, decode
    data_blob = encode_data_blob(data, data_format, factor_millivolts)
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts)

    # compare input <-> decoded
    assert_array_equal(data_decoded, data)


@pytest.mark.parametrize("factor_millivolts", (1, 0.1, 0.01, 0.001))
@pytest.mark.parametrize("data_format", (0, 2))
def test_encode_decode_f32_to_f32(data_format: int, factor_millivolts: float):
    # calculate max amplitude to prevent clipping float32 -> int16
    ii16 = np.iinfo(np.int16)
    max_amplitude = ii16.max * 1e-3 * factor_millivolts
    # generate data with floats in possible range
    data = np.linspace(-max_amplitude, max_amplitude, 2**15, endpoint=True, dtype=np.float32)

    # encode, decode
    data_blob = encode_data_blob(data, data_format, factor_millivolts)
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts)

    # compare input <-> decoded
    assert len(data_decoded) == len(data)

    adc_step = max_amplitude * (2 ** -15)
    assert_allclose(data_decoded, data, atol=adc_step, rtol=0)  # why so high tolerance necessary?


@pytest.mark.parametrize("factor_millivolts", (1, 0.001))
@pytest.mark.parametrize("data_format", (0, 2))
def test_decode_encode_blob_to_blob(data_format: int, factor_millivolts: float):
    def generate_random_blob():
        # calculate max amplitude to prevent clipping float32 -> int16
        ii16 = np.iinfo(np.int16)
        max_amplitude = ii16.max * 1e-3 * factor_millivolts
        # generate random data
        data = max_amplitude * (2 * np.random.rand(1024) - 1)
        # encode to blob
        return encode_data_blob(data, data_format, factor_millivolts)

    data_blob = generate_random_blob()

    # decode, encode
    data_decoded = decode_data_blob(data_blob, data_format, factor_millivolts)
    data_blob_2 = encode_data_blob(data_decoded, data_format, factor_millivolts)

    assert data_blob == data_blob_2
