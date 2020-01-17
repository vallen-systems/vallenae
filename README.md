# Vallen AE Python Tools

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://travis-ci.org/vallen-systems/pyVallenAE.svg?branch=master)](https://travis-ci.org/vallen-systems/pyVallenAE)
[![Documentation Status](https://readthedocs.org/projects/pyvallenae/badge/?version=latest)](https://pyvallenae.readthedocs.io/en/latest/?badge=latest)

Python tools to extract and analyze Acoustic Emission measurement data:

- vallenae.**io**: Reading (and writing) of Vallen Systeme SQLite database files (*.pridb, *.tradb, *.trfdb)
- vallenae.**features**: Extraction of Acoustic Emission features
- vallenae.**timepicker**: Timepicking algorithms for arrival time estimations

## Documentation

See https://pyvallenae.readthedocs.io/en/latest/ for a complete reference manual and examples.

## Installation

Install the latest version for PyPI:

```
pip install vallenae
```

Alternatively, you can download or clone the repository and install it with pip:
```
git clone https://github.com/vallen-systems/pyVallenAE.git
pip install -e pyVallenAE
```
