Changelog
=========

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