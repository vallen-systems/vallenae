"""
Features
========

Acoustic Emission
-----------------

.. autosummary::
    :toctree: generated

    peak_amplitude
    peak_amplitude_index
    is_above_threshold
    first_threshold_crossing
    rise_time
    energy
    signal_strength
    counts
    rms

Conversion
----------

.. autosummary::
    :toctree: generated

    amplitude_to_db
    db_to_amplitude
"""

# flake8: noqa

from .acoustic_emission import *
from .conversion import *

__all__ = [_ for _ in dir() if not _.startswith("_")]
