-- Replace constant {timebase} with Python string format
-- Tables
CREATE TABLE acq_setup (
    ID INTEGER PRIMARY KEY,
    Data TEXT
);

CREATE TABLE ae_data (
    "SetID" INTEGER PRIMARY KEY,
    "SetType" INT,
    "Time" INT,
    "Chan" INT,
    "Status" INT,
    "ParamID" INT,
    "Thr" INT,
    "Amp" INT,
    "RiseT" INT,
    "Dur" INT,
    "Eny" INT,
    "SS" INT,
    "RMS" INT,
    "Counts" INT,
    "TRAI" INT,
    "CCnt" INT,
    "CEny" INT,
    "CSS" INT,
    "CHits" INT,
    "PCTD" INT,
    "PCTA" INT
);

CREATE TABLE ae_fieldinfo (
    "field",
    "Unit",
    "SetTypes",
    "Parameter",
    "Factor"
);

CREATE TABLE ae_globalinfo (
    "Key" UNIQUE,
    "Value"
);

CREATE TABLE ae_markers (
    "SetID" INT UNIQUE,
    "Number" INT,
    "Data" TEXT
);

CREATE TABLE ae_params (
    "ID" INTEGER PRIMARY KEY,
    "SetupID" INT,
    "Chan" INT,
    "ADC_µV" REAL,
    "ADC_TE" REAL,
    "ADC_SS" REAL
);

CREATE TABLE data_integrity (
    "TableName" TEXT PRIMARY KEY UNIQUE,
    "HashV1" INT,
    "LastRow" INT
);

-- Indexes
CREATE INDEX idx_SetupID_Chan ON ae_params (SetupID, Chan);

-- Views
CREATE VIEW view_ae_data AS
    SELECT
        (d.SetID) AS SetID,
        (d.SetType) AS SetType,
        (d.Time * 1.0 / {timebase}) AS Time,
        (d.Chan) AS Chan,
        (d.Status) AS Status,
        (d.Thr * p.ADC_µV) as Thr,
        (d.Amp * p.ADC_µV) AS Amp,
        (d.RiseT * 1e6 / {timebase}) as RiseT,
        (d.Dur * 1e6 / {timebase}) AS Dur,
        (d.Eny * p.ADC_TE) AS Eny,
        (d.SS * p.ADC_SS) AS SS,
        (d.RMS * 0.0065536 * p.ADC_µV) AS RMS,
        (d.Counts) as Counts,
        (d.TRAI) AS TRAI,
        (d.CCnt) AS CCnt,
        (d.CEny * p.ADC_TE) AS CEny,
        (d.CSS * p.ADC_SS) AS CSS,
        (d.CHits) AS CHits,
        (d.PCTD) AS PCTD,
        (d.PCTA) AS PCTA
    FROM ae_data d
    LEFT JOIN ae_params p ON p.ID=d.ParamID;

CREATE VIEW view_ae_markers AS
    SELECT
        m.*,
        l.SetType,
        (l.Time * 1.0 / {timebase}) AS Time
    FROM ae_markers m
    CROSS JOIN ae_data l ON l.SetID = m.SetID;

-- Insert fieldinfo
INSERT INTO ae_fieldinfo VALUES("Time", "[s]", NULL, NULL, 1.0 / {timebase});
INSERT INTO ae_fieldinfo VALUES("Chan", NULL, 12, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("Status", NULL, 14, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("ParamID", NULL, 14, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("Thr", "[µV]", 12, "ADC_µV", NULL);
INSERT INTO ae_fieldinfo VALUES("Amp", "[µV]", 4, "ADC_µV", NULL);
INSERT INTO ae_fieldinfo VALUES("RiseT", "[µs]", 4, NULL, 1e6 / {timebase});
INSERT INTO ae_fieldinfo VALUES("Dur", "[µs]", 4, NULL, 1e6 / {timebase});
INSERT INTO ae_fieldinfo VALUES("Eny", "[eu]", 12, "ADC_TE", NULL);
INSERT INTO ae_fieldinfo VALUES("SS", "[nVs]", 12, "ADC_SS", NULL);
INSERT INTO ae_fieldinfo VALUES("RMS", "[µV]", 12, "ADC_µV", 0.00655356);
INSERT INTO ae_fieldinfo VALUES("Counts", NULL, 4, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("TRAI", NULL, 4, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("CCnt", NULL, 4, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("CEny", "[eu]", 4, "ADC_TE", NULL);
INSERT INTO ae_fieldinfo VALUES("CSS", "[nVs]", 4, "ADC_SS", NULL);
INSERT INTO ae_fieldinfo VALUES("CHits", NULL, 4, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("PCTD", NULL, 2, NULL, NULL);
INSERT INTO ae_fieldinfo VALUES("PCTA", NULL, 2, NULL, NULL);

-- Insert globalinfo
INSERT INTO ae_globalinfo (Key, Value) VALUES ("Version", 1);
INSERT INTO ae_globalinfo (Key, Value) VALUES ("FileStatus", 0);
INSERT INTO ae_globalinfo (Key, Value) VALUES ("TimeBase", {timebase});
INSERT INTO ae_globalinfo (Key, Value) VALUES ("WriterID", "-");
INSERT INTO ae_globalinfo (Key, Value) VALUES ("FileID", NULL);  -- GUID
INSERT INTO ae_globalinfo (Key, Value) VALUES ("ValidSets", 0);
INSERT INTO ae_globalinfo (Key, Value) VALUES ("TRAI", 0);
