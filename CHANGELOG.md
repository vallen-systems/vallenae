# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.3] - 2020-05-04

### Fixed

- SQLite URI for absolute linux paths

## [0.5.2] - 2020-05-04

### Fixed

- SQLite URI for special characters (#, ?)

## [0.5.1] - 2020-03-25

### Fixed

- Buffering of SQL results in `listen` methods to allow SQL queries in between

## [0.5.0] - 2020-03-18

### Added

- Query filter parameter to `TrfDatabase.read` and `TrfDatabase.iread`
- `listen` method for `PriDatabase`, `TraDatabase` and `TrfDatabase` to retrieve new records live

### Changed

- Order feature records by TRAI for `TrfDatabase.read` and `TrfDatabase.iread`

## [0.4.0] - 2021-02-14

### Added

- CI with GitHub actions on Linux, MacOS and Windows
- Workflow with GitHub actions to publish to PyPI on new releases
- `pyproject.toml` as the main config file for pylint, pytest, tox, coverage, ...

### Changed

- Return exact time range with `TraDatabase.read_continuous_wave`
- Return "absolute" time axis with `TraDatabase.read_continuous_wave`
  (instead of starting at t = 0 s)

### Fixed

- Fix database close if exception raised in `__init__` (e.g. file not found)
- Example `ex6_multiprocessing` for MacOS
- Find lower/upper bounds for same values (times) in binary search (used by `TraDatabase.iread`)
- Stop condition for `time_stop` in `TraDatabase.iread`
- Use TRAI for `TraDatabase.iread` as a time sorted index for binary search (SetID is not!)
- Check for empty time ranges in `TraDatabase.iread`

## [0.3.0] - 2020-11-05

### Added

- Query filter for pridb/tradb (i)read functions

## [0.2.4] - 2020-11-01

### Fixed

- SQL schemas for pridb/tradb/trfdb creation, add fieldinfos

## [0.2.3] - 2020-09-01

### Fixed

- AIC timepicker
- Add threshold for monotonic time check (1 ns) to ignore rounding issues
- Suppress exception chaining

## [0.2.2] - 2020-07-10

### Added

- Database classes are now pickable and can be used in multiprocessing
- SQLite transactions for all writes
- Faster blob encoding (`vallenae.io.encode_data_blob`)
- Faster RMS computation with Numba (`vallenae.features.rms`)

### Fixed

- Catch possible global_info table parsing errors 

## [0.2.1] - 2020-02-10

### Fixed

- Examples outputs if not run as notebook
- Out-of-bound time_start, time_stop with SQL binary search
- Optional signal strength for e.g. spotWave data acquisition

## [0.2.0] - 2020-02-06

### Added

- Database creation with `mode="rwc"`, e.g. `vallenae.io.PriDatabase.__init__`

### Fixed

- Number field in `vallenae.io.MarkerRecord` optional
- Scaling of parametric inputs optional
- Keep column order of query if new columns are added to the database
- Return array with float32 from `vallenae.io.TraDatabase.read_continuous_wave` (instead of float64)

## [0.1.0] - 2020-01-24

Initial public release

[Unreleased]: https://github.com/vallen-systems/pyVallenAE/compare/0.5.3...HEAD
[0.5.3]: https://github.com/vallen-systems/pyVallenAE/compare/0.5.2...0.5.3
[0.5.2]: https://github.com/vallen-systems/pyVallenAE/compare/0.5.1...0.5.2
[0.5.1]: https://github.com/vallen-systems/pyVallenAE/compare/0.5.0...0.5.1
[0.5.0]: https://github.com/vallen-systems/pyVallenAE/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/vallen-systems/pyVallenAE/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/vallen-systems/pyVallenAE/compare/0.2.3...0.3.0
[0.2.4]: https://github.com/vallen-systems/pyVallenAE/compare/0.2.3...0.2.4
[0.2.3]: https://github.com/vallen-systems/pyVallenAE/compare/0.2.2...0.2.3
[0.2.2]: https://github.com/vallen-systems/pyVallenAE/compare/0.2.1...0.2.2
[0.2.1]: https://github.com/vallen-systems/pyVallenAE/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/vallen-systems/pyVallenAE/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/vallen-systems/pyVallenAE/releases/tag/0.1.0
