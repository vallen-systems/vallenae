Vallen AE Python Tools
======================

Extract and analyze Acoustic Emission measurement data.

The IO module :mod:`vallenae.io` enables reading (and writing) of Vallen Systeme SQLite database files:

- **\*.pridb**: Primary database
- **\*.tradb**: Transient data
- **\*.trfdb**: Transient features

The remaining modules are system-independent and try to comprise the most common state-of-the-art algorithms in Acoustic Emission:

- :mod:`vallenae.features`: Extraction of Acoustic Emission features
- :mod:`vallenae.timepicker`: Timepicking algorithms for arrival time estimations
- :mod:`vallenae.processor`: Processors -- e.g. grouping hits into events

Library modules
---------------

.. autosummary::
    :caption: Library documentation
    :toctree: generated

    vallenae.io
    vallenae.features
    vallenae.timepicker
    vallenae.processor

.. toctree::
    :caption: Examples
    :maxdepth: 1
    :hidden:

    _examples/index

.. toctree::
    :caption: Development
    :maxdepth: 1
    :hidden:

    changelog

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
