"""
Timerpicker
===========

The determination of signal arrival times has a major influence on the localization accuracy.
Usually, arrival times are determined by the first threshold crossing (either fixed or adaptive).
Following popular methods have been proposed in the past to automatically pick time of arrivals:

.. autosummary::
    :toctree: generated

    hinkley
    aic
    energy_ratio
    modified_energy_ratio
"""

# flake8: noqa

from .timepicker import *

__all__ = [_ for _ in dir() if not _.startswith("_")]
