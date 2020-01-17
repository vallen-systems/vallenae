"""
IO
==

Read/write Vallen Systeme database and setup files.

Database classes
----------------

Classes to read/write pridb and tradb database files.

.. warning:: Writing is still experimental

.. autosummary::
    :toctree: generated

    PriDatabase
    TraDatabase

All database classes implement two different interfaces to access data:

**Standard** ``read_*``

    Read data to `pandas.DataFrame`, e.g. with `PriDatabase.read_hits`

    >>> pridb = vae.io.PriDatabase("./examples/steel_plate/sample.pridb")
    >>> df = pridb.read_hits()  # save all hits to pandas dataframe
    >>> df[["time", "channel"]]  # output columns hit and channel
                time  channel
    set_id
    10      3.992771        3
    11      3.992775        2
    12      3.992813        4
    13      3.992814        1

**Streaming** ``iread_*``

    Iterate through the data row by row.
    This is a memory-efficient solution ideal for batch processing.
    The return types are specific `typing.NamedTuple`, see :ref:`datatypes`.

    Example with `PriDatabase.iread_hits`:

    >>> pridb = vae.io.PriDatabase("./examples/steel_plate/sample.pridb")
    >>> for hit in pridb.iread_hits():
    ...     print("time: {:0.4f}, channel: {:d}".format(hit.time, hit.channel))
    ...
    time: 3.9928,   channel: 3
    time: 3.9928,   channel: 2
    time: 3.9928,   channel: 4
    time: 3.9928,   channel: 1
    >>> type(hit)
    <class 'vallenae.io.datatypes.HitRecord'>


.. _datatypes:

Data types
----------

Records of the database are represented as `typing.NamedTuple`.
Each record implements a class method ``from_sql`` to init from a SQLite
row dictionary (column name: value).

.. autosummary::
    :toctree: generated

    HitRecord
    MarkerRecord
    StatusRecord
    ParametricRecord
    TraRecord

Compression
-----------

Transient signals in the tradb are stored as BLOBs of 16-bit ADC values --
either uncompressed or compressed (`FLAC <https://xiph.org/flac/>`_).
Following functions convert between BLOBs and arrays of voltage values.

.. autosummary::
    :toctree: generated

    decode_data_blob
    encode_data_blob
"""

# flake8: noqa

from .datatypes import *
from .types import *
from .compression import *
from .pridb import *
from .tradb import *

__all__ = [_ for _ in dir() if not _.startswith("_")]
