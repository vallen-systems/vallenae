import math


def amplitude_to_db(amplitude: float, reference: float = 1e-6) -> float:
    """
    Convert amplitude from volts to decibel (dB).

    Args:
        amplitude: Amplitude in volts
        reference: Reference amplitude. Defaults to 1 µV for dB(AE)

    Returns:
        Amplitude in dB(ref)
    """
    return 20 * math.log10(amplitude / reference)


def db_to_amplitude(amplitude_db: float, reference: float = 1e-6) -> float:
    """
    Convert amplitude from decibel (dB) to volts.

    Args:
        amplitude_db: Amplitude in dB
        reference: Reference amplitude. Defaults to 1 µV for dB(AE)

    Returns:
        Amplitude in volts
    """
    return reference * 10 ** (amplitude_db / 20)
