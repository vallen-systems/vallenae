-- Replace constant {timebase} with Python string format
-- Tables
CREATE TABLE tr_data (
    "SetID" INTEGER PRIMARY KEY,
    "Time" INT,
    "TRAI" INT,
    "Status" INT,
    "ParamID" INT,
    "Chan" INT,
    "Pretrigger" INT,
    "Thr" INT,
    "SampleRate" INT,
    "Samples" INT,
    "DataFormat" INT,
    "Data" BLOB
);

CREATE TABLE tr_fieldinfo (
    "field",
    "Unit",
    "Parameter"
);

CREATE TABLE tr_globalinfo (
    "Key" UNIQUE,
    "Value"
);

CREATE TABLE tr_params (
    "ID" INTEGER PRIMARY KEY,
    "SetupID" INT,
    "Chan" INT,
    "ADC_µV" REAL,
    "TR_mV" REAL
);

-- Indexes
CREATE INDEX idx_TRAI on tr_data (TRAI);
CREATE INDEX idx_SetupID_Chan on tr_params (SetupID, Chan);

-- Views
CREATE VIEW view_tr_data AS
    SELECT
        (d.SetID) AS SetID,
        (d.Time * 1.0 / {timebase}) AS Time,
        (d.TRAI) AS TRAI,
        (d.Status) AS Status,
        (d.Chan) AS Chan,
        (d.Pretrigger) AS Pretrigger,
        (d.Thr * p.ADC_µV) AS Thr,
        (d.SampleRate) AS SampleRate,
        (d.Samples) AS Samples,
        (d.DataFormat) AS DataFormat,
        (p.TR_mV) AS TR_mV,
        (d.Data) AS Data
    FROM tr_data d
    LEFT JOIN tr_params p ON p.ID=d.ParamID;

-- Insert fieldinfo
INSERT INTO tr_fieldinfo VALUES("Time", "[s]", NULL);
INSERT INTO tr_fieldinfo VALUES("Thr", "[µV]", "ADC_µV");
INSERT INTO tr_fieldinfo VALUES("SampleRate", "[Hz]", NULL);
INSERT INTO tr_fieldinfo VALUES("Data", NULL, "TR_mV");

-- Insert globalinfo
INSERT INTO tr_globalinfo (Key, Value) VALUES ("Version", 1);
INSERT INTO tr_globalinfo (Key, Value) VALUES ("FileStatus", 0);
INSERT INTO tr_globalinfo (Key, Value) VALUES ("TimeBase", {timebase});
INSERT INTO tr_globalinfo (Key, Value) VALUES ("BytesPerSample", 2);
INSERT INTO tr_globalinfo (Key, Value) VALUES ("WriterID", "-");
INSERT INTO tr_globalinfo (Key, Value) VALUES ("FileID", NULL);  -- GUID
INSERT INTO tr_globalinfo (Key, Value) VALUES ("ReferenceID", NULL);  -- GUID of pridb
INSERT INTO tr_globalinfo (Key, Value) VALUES ("ValidSets", 0);
INSERT INTO tr_globalinfo (Key, Value) VALUES ("TRAI", 0);
