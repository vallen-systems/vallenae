from functools import wraps
from typing import Set, Optional, Union, Sequence
from pathlib import Path
import pandas as pd

from ._database import Database, require_write_access
from ._dataframe import iter_to_dataframe
from ._sql import (
    QueryIterable,
    query_conditions,
    create_new_database,
    insert_from_dict,
)
from .datatypes import HitRecord, MarkerRecord, ParametricRecord, StatusRecord
from .types import SizedIterable


RecordType = Union[HitRecord, MarkerRecord, ParametricRecord, StatusRecord]


def check_monotonic_time(func):
    def get_max_time(database: "PriDatabase"):
        con = database.connection()
        cur = con.execute("SELECT Time FROM view_ae_data ORDER BY SetID DESC LIMIT 1")
        try:
            return cur.fetchone()[0]  # None is not subscriptable -> TypeError
        except TypeError:
            return 0

    @wraps(func)
    def wrapper(self: "PriDatabase", record: RecordType, *args, **kwargs):
        max_time = get_max_time(self)
        if record.time < max_time:
            raise ValueError(
                (
                    f"Time column has to be monotonic increasing."
                    f"Time of current / last row: {record.time} / {max_time} s"
                )
            )
        return func(self, record, *args, **kwargs)
    return wrapper


class PriDatabase(Database):
    """IO Wrapper for pridb database file."""

    def __init__(self, filename: str, *, readonly: bool = True):
        """
        Open pridb database file.

        Args:
            filename: Path to pridb database file
            readonly: Open database in read-only mode (`True`) or read-write mode (`False`)
        """
        super().__init__(
            filename, table_prefix="ae", readonly=readonly, required_file_ext="pridb",
        )
        self._timebase = self.globalinfo()["TimeBase"]

    def channel(self) -> Set[int]:
        """Get list of channels."""
        con = self.connection()
        cur = con.execute("SELECT DISTINCT Chan FROM ae_data WHERE Chan IS NOT NULL")
        return {result[0] for result in cur.fetchall()}

    def read_hits(self, **kwargs) -> pd.DataFrame:
        """
        Read hits to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread_hits`

        Returns:
            Pandas DataFrame with hit data
        """
        return iter_to_dataframe(
            self.iread_hits(**kwargs), desc="Hits", index_column="set_id",
        )

    def read_markers(self, **kwargs) -> pd.DataFrame:
        """
        Read marker to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread_markers`

        Returns:
            Pandas DataFrame with marker data
        """
        df = iter_to_dataframe(
            self.iread_markers(**kwargs), desc="Marker", index_column="set_id",
        )
        # set column dtypes
        df.number = df.number.astype(pd.Int64Dtype())
        df.data = df.data.astype(str)
        return df

    def read_parametric(self, **kwargs) -> pd.DataFrame:
        """
        Read parametric data to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread_parametric`

        Returns:
            Pandas DataFrame with parametric data
        """
        return iter_to_dataframe(
            self.iread_parametric(**kwargs), desc="Parametric", index_column="set_id",
        )

    def read_status(self, **kwargs) -> pd.DataFrame:
        """
        Read status data to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread_status`

        Returns:
            Pandas DataFrame with status data
        """
        return iter_to_dataframe(
            self.iread_status(**kwargs), desc="Status", index_column="set_id",
        )

    def read(self, **kwargs) -> pd.DataFrame:
        """
        Read all data set types (hits, markers, parametric data, status data)
        from pridb to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread_hits`, `iread_markers`, `iread_parametric`
                and `iread_status`

        Returns:
            Pandas DataFrame with all pridb data set types
        """
        # read to separate dataframes
        df_hits = self.read_hits(**kwargs)
        df_markers = self.read_markers(**kwargs)
        df_parametric = self.read_parametric(**kwargs)
        df_status = self.read_status(**kwargs)

        # add missing set_types
        column_set_type = 0
        df_hits.insert(column_set_type, "set_type", 2)
        df_parametric.insert(column_set_type, "set_type", 1)
        df_status.insert(column_set_type, "set_type", 3)

        # drop additional marker columns
        df_markers.drop(columns=["number", "data"], inplace=True)

        # dict to restore original data types
        dtypes = {
            **dict(df_hits.dtypes),
            **dict(df_markers.dtypes),
            **dict(df_parametric.dtypes),
            **dict(df_status.dtypes),
        }

        # concat all dataframes, restore types and sort by index
        df = (
            pd.concat(
                [df_markers, df_hits, df_status, df_parametric], sort=False, copy=False
            )
            .apply(lambda x: x.astype(dtypes[x.name]))
            .sort_index()
            .rename_axis(df_hits.index.name)
        )
        return df

    def iread_hits(
        self,
        *,
        channel: Union[None, int, Sequence[int]] = None,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        set_id: Union[None, int, Sequence[int]] = None,
    ) -> SizedIterable[HitRecord]:
        """
        Stream hits with returned iterable.

        Args:
            channel: None if all channels should be read.
                Otherwise specify the channel number or a list of channel numbers
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            set_id: Read by SetID

        Returns:
            Sized iterable to sequential read hits
        """
        query = """
        SELECT vae.*, ae.ParamID
        FROM view_ae_data vae
        LEFT JOIN ae_data ae ON vae.SetID == ae.SetID
        """ + query_conditions(
            equal={"vae.SetType": 2},
            isin={"vae.Chan": channel, "vae.SetID": set_id},
            greater_equal={"vae.Time": time_start},
            less={"vae.Time": time_stop},
        )
        return QueryIterable(self.connection(), query, HitRecord.from_sql)

    def iread_markers(
        self,
        *,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        set_id: Union[None, int, Sequence[int]] = None,
    ) -> SizedIterable[MarkerRecord]:
        """
        Stream markers with returned iterable.

        Args:
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            set_id: Read by SetID

        Returns:
            Sized iterable to sequential read markers
        """
        query = """
        SELECT SetID, Time, SetType, Number, Data
        FROM view_ae_markers vae
        """ + query_conditions(
            isin={"vae.SetID": set_id},
            greater_equal={"vae.Time": time_start},
            less={"vae.Time": time_stop},
        )
        return QueryIterable(self.connection(), query, MarkerRecord.from_sql)

    def iread_parametric(
        self,
        *,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        set_id: Union[None, int, Sequence[int]] = None,
    ) -> SizedIterable[ParametricRecord]:
        """
        Stream parametric data with returned iterable.

        Args:
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            set_id: Read by SetID

        Returns:
            Sized iterable to sequential read parametric data
        """
        query = """
        SELECT vae.*, ae.ParamID
        FROM view_ae_data vae
        LEFT JOIN ae_data ae ON vae.SetID == ae.SetID
        """ + query_conditions(
            equal={"vae.SetType": 1},
            isin={"vae.SetID": set_id},
            greater_equal={"vae.Time": time_start},
            less={"vae.Time": time_stop},
        )
        return QueryIterable(self.connection(), query, ParametricRecord.from_sql)

    def iread_status(
        self,
        *,
        channel: Union[None, int, Sequence[int]] = None,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        set_id: Union[None, int, Sequence[int]] = None,
    ) -> SizedIterable[StatusRecord]:
        """
        Stream status data with returned iterable.

        Args:
            channel: None if all channels should be read.
                Otherwise specify the channel number or a list of channel numbers
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            set_id: Read by SetID

        Returns:
            Sized iterable to sequential read status data
        """
        query = """
        SELECT vae.*, ae.ParamID
        FROM view_ae_data vae
        LEFT JOIN ae_data ae ON vae.SetID == ae.SetID
        """ + query_conditions(
            equal={"vae.SetType": 3},
            isin={"vae.Chan": channel, "vae.SetID": set_id},
            greater_equal={"vae.Time": time_start},
            less={"vae.Time": time_stop},
        )
        return QueryIterable(self.connection(), query, StatusRecord.from_sql)

    @require_write_access
    @check_monotonic_time
    def write_hit(self, hit: HitRecord):
        """
        Write hit to pridb.

        Caution: `HitRecord.set_id` is ignored and automatically incremented.

        Args:
            hit: Hit data set

        Returns:
            Index (SetID) of inserted row

        Todo:
            Status flag
        """
        parameter = self._parameter(hit.param_id)
        return insert_from_dict(
            self.connection(),
            self._table_main,
            {
                "SetType": 2,
                "Time": int(hit.time * self._timebase),
                "Chan": hit.channel,
                "Status": 0,
                "ParamID": hit.param_id,
                "Thr": int(hit.threshold * 1e6 / parameter["ADC_µV"]),
                "Amp": int(hit.amplitude * 1e6 / parameter["ADC_µV"]),
                "RiseT": int(hit.rise_time * self._timebase),
                "Dur": int(hit.duration * self._timebase),
                "Eny": int(hit.energy / parameter["ADC_TE"]),
                "SS": int(hit.signal_strength / parameter["ADC_SS"]),
                "RMS": int(hit.rms * 1e6 / parameter["ADC_µV"] / 0.0065536),
                "Counts": hit.counts,
                "TRAI": hit.trai,
            },
        )

    @require_write_access
    @check_monotonic_time
    def write_marker(self, marker: MarkerRecord):
        """
        Write marker to pridb.

        Caution: `MarkerRecord.set_id` is ignored and automatically incremented.

        Args:
            marker: Marker data set

        Returns:
            Index (SetID) of inserted row
        """
        set_id = insert_from_dict(
            self.connection(),
            self._table_main,
            {
                "SetType": int(marker.set_type),
                "Time": int(marker.time * self._timebase),
            },
        )
        insert_from_dict(
            self.connection(),
            "ae_markers",
            {
                "SetID": set_id,
                "Number": marker.number,
                "Data": marker.data,
            },
        )
        return set_id

    @require_write_access
    @check_monotonic_time
    def write_status(self, status: StatusRecord):
        """
        Write status data to pridb.

        Caution: `StatusRecord.set_id` is ignored and automatically incremented.

        Args:
            status: Status data set

        Returns:
            Index (SetID) of inserted row
        """
        parameter = self._parameter(status.param_id)
        return insert_from_dict(
            self.connection(),
            self._table_main,
            {
                "SetType": 3,
                "Time": int(status.time * self._timebase),
                "Chan": status.channel,
                "Status": 0,
                "ParamID": status.param_id,
                "Thr": int(status.threshold * 1e6 / parameter["ADC_µV"]),
                "Eny": int(status.energy / parameter["ADC_TE"]),
                "SS": int(status.signal_strength / parameter["ADC_SS"]),
                "RMS": int(status.rms * 1e6 / parameter["ADC_µV"] / 0.0065536),
            },
        )

    @require_write_access
    @check_monotonic_time
    def write_parametric(self, parametric: ParametricRecord):
        """
        Write parametric data to pridb.

        Caution: `ParametricRecord.set_id` is ignored and automatically incremented.

        Args:
            parametric: Parametric data set

        Returns:
            Index (SetID) of inserted row

        Todo:
            Status flag
        """
        parameter = self._parameter(parametric.param_id)
        return insert_from_dict(
            self.connection(),
            self._table_main,
            {
                "SetType": 1,
                "Time": int(parametric.time * self._timebase),
                "Status": 0,
                "ParamID": parametric.param_id,
                "PCTD": parametric.pctd,
                "PCTA": parametric.pcta,
                "PA0": int(parametric.pa0 / parameter["PA0_mV"]) if parametric.pa0 else None,
                "PA1": int(parametric.pa1 / parameter["PA1_mV"]) if parametric.pa1 else None,
            },
        )


def create_empty_pridb(filename: str):
    file_schema = Path(__file__).resolve().parent / "schema_templates/pridb.sql"
    with open(file_schema, "r") as file:
        schema = file.read()
    schema = schema.format(timebase=int(1e7))  # fill placeholder / constants
    create_new_database(filename, schema)
