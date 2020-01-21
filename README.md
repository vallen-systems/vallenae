# Vallen AE Python Tools

[![Build Status](https://travis-ci.org/vallen-systems/pyVallenAE.svg?branch=master)](https://travis-ci.org/vallen-systems/pyVallenAE)
[![Documentation Status](https://readthedocs.org/projects/pyvallenae/badge/?version=latest)](https://pyvallenae.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/vallen-systems/pyVallenAE/badge.svg?branch=dev)](https://coveralls.io/github/vallen-systems/pyVallenAE)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Python tools to extract and analyze Acoustic Emission measurement data:

- vallenae.**io**: Reading (and writing) of Vallen Systeme SQLite database files (*.pridb, *.tradb, *.trfdb)
- vallenae.**features**: Extraction of Acoustic Emission features
- vallenae.**timepicker**: Timepicking algorithms for arrival time estimations

## Documentation

For full documentation and examples, please visit http://pyvallenae.rtfd.io.

## Installation

Install the latest version from PyPI:

```
pip install vallenae
```

Please note, that `vallenae` requires Python 3.6 or newer. On Linux systems, `pip` is usually mapped to Python 2, so use `pip<version>` (e.g. `pip3` or `pip3.7`) instead. Alternatively, you can run `pip` from your specific Python version with `python<version> -m pip`.

## Contributing

Feature requests, bug reports and fixes are always welcome!

After cloning the repository, you can easily install the development environment and tools 
([pylint](https://www.pylint.org), [mypy](http://mypy-lang.org), [pytest](https://pytest.org), [tox](https://tox.readthedocs.io))
with:

```
git clone https://github.com/vallen-systems/pyVallenAE.git
cd pyVallenAE
pip install -e .[dev]
```

And run the test suite with tox:

```
tox
```

The documentation is built with [sphinx](https://www.sphinx-doc.org):

```
cd docs
sphinx-build . _build
```