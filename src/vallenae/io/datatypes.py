from typing import NamedTuple, Optional, Dict, Any
import numpy as np

from .compression import decode_data_blob


class HitRecord(NamedTuple):
    """
    Hit record in pridb (SetType = 2).
    """

    time: float  #: Time in seconds
    channel: int  #: Channel number
    param_id: int  #: Parameter ID of table ae_params for ADC value conversion
    threshold: float  #: Threshold amplitude in volts
    amplitude: float  #: Peak amplitude in volts
    rise_time: float  #: Rise time in seconds
    duration: float  #: Hit duration in seconds
    energy: float  #: Energy (EN 1330-9) in eu (1e-14 V²s)
    signal_strength: float  #: Signal strength in nVs (1e-9 Vs)
    rms: float  #: RMS of the noise before the hit in volts
    counts: int  #: Number of possitive threshold crossings
    trai: Optional[int] = None  #: Transient recorder index (foreign key between pridb and tradb)
    cascade_hits: Optional[int] = None  #: Total number of hits in the same hit-cascade
    cascade_counts: Optional[int] = None  #: Summed counts of hits in the same hit-cascade
    cascade_energy: Optional[int] = None  #: Summed energy of hits in the same hit-cascade
    cascade_signal_strength: Optional[int] = None  #: Summed signal strength of hits in the same hit-cascade  # noqa  # pylint: disable=line-too-long
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "HitRecord":
        """
        Create HitRecord from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            threshold=row["Thr"] / 1e6,  # µV -> V
            amplitude=row["Amp"] / 1e6,  # µV -> V
            rise_time=row["RiseT"] / 1e6,  # µs -> s
            duration=row["Dur"] / 1e6,  # µs -> s
            energy=row["Eny"],
            signal_strength=row["SS"],
            rms=row["RMS"] / 1e6,  # µV -> V
            counts=row["Counts"],
            trai=row["TRAI"],
            cascade_hits=row.get("CHits", None),
            cascade_counts=row.get("CCnt", None),
            cascade_energy=row.get("CEny", None),
            cascade_signal_strength=row.get("CSS", None),
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
    number: int  #: Number of marker (unique? asc?)
    data: str  #: Content of marker (label text or datetime)
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "MarkerRecord":
        """
        Create MarkerRecord from SQL row.

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
    threshold: float  #: Threshold amplitude in volts
    energy: float  #: Energy (EN 1330-9) in eu (1e-14 V²s)
    signal_strength: float  #: Signal strength in nVs (1e-9 Vs)
    rms: float  #: RMS in volts
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "StatusRecord":
        """
        Create StatusRecord from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            threshold=row["Thr"] / 1e6,  # µV -> V
            energy=row["Eny"],
            signal_strength=row["SS"],
            rms=row["RMS"] / 1e6,  # µV -> V
        )


class ParametricRecord(NamedTuple):
    """
    Parametric data record in pridb (SetType = 1).
    """

    time: float  #: Time in seconds
    param_id: int  #: Parameter ID of table ae_params for ADC value conversion
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
    set_id: Optional[int] = None  #: Unique identifier for data set in pridb

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "ParametricRecord":
        """
        Create ParametricRecord from SQL row.

        Args:
            row: Dict of column names and values
        """
        return cls(
            set_id=row["SetID"],
            time=row["Time"],
            param_id=row["ParamID"],
            pctd=row.get("PCTD", None),
            pcta=row.get("PCTA", None),
            pa0=row.get("PA0", None),
            pa1=row.get("PA1", None),
            pa2=row.get("PA2", None),
            pa3=row.get("PA3", None),
            pa4=row.get("PA4", None),
            pa5=row.get("PA5", None),
            pa6=row.get("PA6", None),
            pa7=row.get("PA7", None),
        )


class TraRecord(NamedTuple):
    """
    Transient data record in tradb.

    Todo:
        Remove RMS
    """

    time: float  #: Time in seconds
    channel: int  #: Channel number
    param_id: int  #: Parameter ID of table tr_params for ADC value conversion
    pretrigger: int  #: Pretrigger samples
    threshold: float  #: Threshold amplitude in volts
    samplerate: int  #: Samplerate in Hz
    samples: int  #: Number of samples
    data_format: int  #: Data format (0 = uncompressed, 2 = FLAC compression)
    data: np.ndarray  #: Transient signal in volts
    trai: Optional[int] = None  #: Transient recorder index (foreign key between pridb and tradb)
    rms: Optional[float] = None  #: RMS of the noise before the hit

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "TraRecord":
        return TraRecord(
            time=row["Time"],
            channel=row["Chan"],
            param_id=row["ParamID"],
            pretrigger=row["Pretrigger"],
            threshold=row["Thr"] / 1e6,  # µV -> V
            samplerate=row["SampleRate"],
            samples=row["Samples"],
            data_format=row["DataFormat"],
            data=decode_data_blob(row["Data"], row["DataFormat"], row["TR_mV"]),
            trai=row["TRAI"],
        )


class FeatureRecord(NamedTuple):
    """
    Transient feature record in trfdb.
    """

    trai: int  #: Transient recorder index
    features: Dict[str, float]  #: Feature dictionary (feature name -> value)

    @classmethod
    def from_sql(cls, row: Dict[str, Any]) -> "FeatureRecord":
        return FeatureRecord(
            trai=row.pop("TRAI"),
            features=row,
        )
