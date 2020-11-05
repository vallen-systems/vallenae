Changelog
=========

0.3.0
-----
2020-11-05

New features
    - Add optional query filter for pridb/tradb (i)read functions 
      (https://github.com/vallen-systems/pyVallenAE/issues/18)


0.2.4
-----
2020-11-01

Bug fixes
    - SQL schemas for pridb/tradb/trfdb creation, add fieldinfos


0.2.3
-----
2020-09-01

Bug fixes
    - AIC timepicker
    - add threshold for monotonic time check (1 ns) to ignore rounding issues
    - suppress exception chaining


0.2.2
-----
2020-07-10

Optimizations
    - database classes are now pickable and can be used in multiprocessing
    - SQLite transactions for all writes
    - faster blob encoding (`vallenae.io.encode_data_blob`)
    - faster RMS computation with Numba (`vallenae.features.rms`)

Bug fixes
    - catch possible global_info table parsing errors 


0.2.1
-----
2020-02-10

Bug fixes
    - examples outputs if not run as notebook
    - out-of-bound time_start, time_stop with SQL binary search
    - optional signal strength for spotWave data acquisition


0.2.0
-----
2020-02-06

New features
    - database creation with `mode="rwc"`, e.g. `vallenae.io.PriDatabase.__init__`

Bug fixes
    - number field in `vallenae.io.MarkerRecord` optional
    - scaling of parametric inputs optional
    - keep column order of query if new columns are added to the database
    - return array with float32 from `vallenae.io.TraDatabase.read_continuous_wave` (instead of float64)


0.1.0
-----
2020-01-24

Initial public release