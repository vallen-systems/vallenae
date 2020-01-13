-- Tables
CREATE TABLE trf_data (
    "TRAI" INT UNIQUE
);

CREATE TABLE trf_globalinfo (
    "Key" UNIQUE,
    "Value"
);

CREATE TABLE trf_fieldinfo (
    "field",
    "SetTypes",
    "Unit",
    "LongName",
    "Description",
    "ShortName",
    "FormatStr"
);
