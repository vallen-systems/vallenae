from typing import Any, Dict, NamedTuple, Optional

import numpy as np

from .compression import decode_data_blob


def _to_volts(value: Optional[float]):
    """Convert µV to V if not None."""
    if value is None:
        return None
    return float(value) / 1e6


def _to_seconds(value: Optional[float]):
    """Convert µs to s if not None."""
    if value is None:
        return None
    return float(value) / 1e6


class HitRecord(NamedTuple):
    """
    Hit record in pridb (SetType = 2).
    """

    time: float  #: Time in seconds
    channel: int  #: Channel number
    param_id: int  #: Parameter ID of table ae_params for ADC value conversion
    amplitude: float  #: Peak amplitude in volts
    duration: float  #: Hit duration in seconds
    energy: float  #: Energy (EN 1330-9) in eu (1e-14 V²s)
    rms: float  #: RMS of the noise before the hit in volts
    # optional for creating:
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb
    threshold: Optional[float] = None  #: Threshold amplitude in volts
    rise_time: Optional[float] = None  #: Rise time in seconds
    signal_strength: Optional[float] = None  #: Signal strength in nVs (1e-9 Vs)
    counts: Optional[int] = None  #: Number of positive threshold crossings
    trai: Optional[int] = None  #: Transient recorder index (foreign key between pridb and tradb)
    cascade_hits: Optional[int] = None  #: Total number of hits in the same hit-cascade
    cascade_counts: Optional[int] = None  #: Summed counts of hits in the same hit-cascade
    cascade_energy: Optional[int] = None  #: Summed energy of hits in the same hit-cascade
    cascade_signal_strength: Optional[int] = None  #: Summed signal strength of hits in the same hit-cascade  # noqa

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "HitRecord":
        """
        Create `HitRecord` from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            threshold=_to_volts(row.get("Thr")),  # optional
            amplitude=_to_volts(row["Amp"]),
            rise_time=_to_seconds(row.get("RiseT")),  # optional
            duration=_to_seconds(row["Dur"]),
            energy=row["Eny"],
            signal_strength=row.get("SS"),  # optional for spotWave
            rms=_to_volts(row["RMS"]),
            counts=row.get("Counts"),  # optional
            trai=row.get("TRAI"),  # optional
            cascade_hits=row.get("CHits"),  # optional
            cascade_counts=row.get("CCnt"),  # optional
            cascade_energy=row.get("CEny"),  # optional
            cascade_signal_strength=row.get("CSS"),  # optional
        )


class MarkerRecord(NamedTuple):
    """
    Marker record in pridb (SetType = 4, 5, 6).

    A marker can have different meanings depending on its SetType:\n
    - 4: label\n
    - 5: datetime data set, as it is inserted whenever recording is started by software\n
    - 6: a section start marker. E.g. new sections are started, if acquisition settings changed
    """

    time: float  #: Time in seconds
    set_type: int  #: Marker type (see above)
    data: str  #: Content of marker (label text or datetime)
    # optional for creating:
    number: Optional[int] = None  #: Marker number
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "MarkerRecord":
        """
        Create `MarkerRecord` from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            set_type=row["SetType"],
            number=row["Number"],
            data=row["Data"],
        )


class StatusRecord(NamedTuple):
    """
    Status data record in pridb (SetType = 3).
    """

    time: float  #: Time in seconds
    channel: int  #: Channel number
    param_id: int  #: Parameter ID of table ae_params for ADC value conversion
    energy: float  #: Energy (EN 1330-9) in eu (1e-14 V²s)
    rms: float  #: RMS in volts
    # optional for creating:
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb
    threshold: Optional[float] = None  #: Threshold amplitude in volts
    signal_strength: Optional[float] = None  #: Signal strength in nVs (1e-9 Vs)

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "StatusRecord":
        """
        Create `StatusRecord` from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            threshold=_to_volts(row.get("Thr")),  # optional
            energy=row["Eny"],
            signal_strength=row.get("SS"),  # optional for spotWave
            rms=_to_volts(row["RMS"]),  # optional
        )


class ParametricRecord(NamedTuple):
    """
    Parametric data record in pridb (SetType = 1).
    """

    time: float  #: Time in seconds
    param_id: int  #: Parameter ID of table ae_params for ADC value conversion
    # optional for creating:
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb
    pctd: Optional[int] = None  #: Digital counter value
    pcta: Optional[int] = None  #: Analog hysteresis counter
    pa0: Optional[int] = None  #: Amplitude of parametric input 0 in volts
    pa1: Optional[int] = None  #: Amplitude of parametric input 1 in volts
    pa2: Optional[int] = None  #: Amplitude of parametric input 2 in volts
    pa3: Optional[int] = None  #: Amplitude of parametric input 3 in volts
    pa4: Optional[int] = None  #: Amplitude of parametric input 4 in volts
    pa5: Optional[int] = None  #: Amplitude of parametric input 5 in volts
    pa6: Optional[int] = None  #: Amplitude of parametric input 6 in volts
    pa7: Optional[int] = None  #: Amplitude of parametric input 7 in volts

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "ParametricRecord":
        """
        Create `ParametricRecord` from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            param_id=row["ParamID"],
            pctd=row.get("PCTD"),  # optional
            pcta=row.get("PCTA"),  # optional
            pa0=row.get("PA0"),  # optional
            pa1=row.get("PA1"),  # optional
            pa2=row.get("PA2"),  # optional
            pa3=row.get("PA3"),  # optional
            pa4=row.get("PA4"),  # optional
            pa5=row.get("PA5"),  # optional
            pa6=row.get("PA6"),  # optional
            pa7=row.get("PA7"),  # optional
        )


class TraRecord(NamedTuple):
    """Transient data record in tradb."""

    time: float  #: Time in seconds
    channel: int  #: Channel number
    param_id: int  #: Parameter ID of table tr_params for ADC value conversion
    pretrigger: int  #: Pretrigger samples
    threshold: float  #: Threshold amplitude in volts
    samplerate: int  #: Samplerate in Hz
    samples: int  #: Number of samples
    data: np.ndarray  #: Transient signal in volts or ADC values if `raw` = `True`
    # optional for writing
    trai: Optional[int] = None  #: Transient recorder index (foreign key between pridb and tradb)
    rms: Optional[float] = None  #: RMS of the noise before the hit
    # optional
    raw: bool = False  #: `data` is stored as ADC values (int16)

    @classmethod
    def from_sql(cls, row: Dict[str, Any], *, raw: bool = False) -> "TraRecord":
        """
        Create `TraRecord` from SQL row.

        Args:
            row: Dict of column names and values
            raw: Provide `data` as ADC values (int16)
        """
        return TraRecord(
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            pretrigger=row["Pretrigger"],
            threshold=_to_volts(row["Thr"]),
            samplerate=row["SampleRate"],
            samples=row["Samples"],
            data=decode_data_blob(row["Data"], row["DataFormat"], row["TR_mV"], raw=raw),
            trai=row["TRAI"],
            raw=raw,
        )


class FeatureRecord(NamedTuple):
    """
    Transient feature record in trfdb.
    """

    trai: int  #: Transient recorder index
    features: Dict[str, float]  #: Feature dictionary (feature name -> value)

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "FeatureRecord":
        """
        Create `FeatureRecord` from SQL row.

        Args:
            row: Dict of column names and values
        """
        return FeatureRecord(
            trai=row.pop("TRAI"),
            features=row,
        )
