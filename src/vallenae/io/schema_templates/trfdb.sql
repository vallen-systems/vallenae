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

-- Insert globalinfo
INSERT INTO trf_globalinfo (Key, Value) VALUES ("Version", 1);
INSERT INTO trf_globalinfo (Key, Value) VALUES ("FileStatus", 0);
INSERT INTO trf_globalinfo (Key, Value) VALUES ("WriterID", "-");
INSERT INTO trf_globalinfo (Key, Value) VALUES ("FileID", NULL);  -- GUID
INSERT INTO trf_globalinfo (Key, Value) VALUES ("ReferenceID", NULL);  -- GUID of pridb
INSERT INTO trf_globalinfo (Key, Value) VALUES ("ValidSets", 0);
