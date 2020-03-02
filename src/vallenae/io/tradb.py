from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from ._database import Database, require_write_access
from ._dataframe import iter_to_dataframe
from ._sql import (
    QueryIterable,
    create_new_database,
    insert_from_dict,
    query_conditions,
    sql_binary_search,
)
from .compression import encode_data_blob
from .datatypes import TraRecord
from .types import SizedIterable


@lru_cache(maxsize=32, typed=True)
def _create_time_vector(
    samples: int, samplerate: int, pretrigger: int = 0
) -> np.ndarray:
    t_raw = np.arange(-pretrigger, samples - pretrigger, dtype=np.int32)
    t_scaled = (t_raw / np.float32(samplerate)).astype(np.float32)
    return t_scaled


class TraDatabase(Database):
    """IO Wrapper for tradb database file."""

    def __init__(
        self, filename: str, mode: str = "ro", *, compression: bool = False,
    ):
        """
        Open tradb database file.

        Args:
            filename: Path to tradb database file
            mode: Define database access:
                **"ro"** (read-only),
                **"rw"** (read-write),
                **"rwc"** (read-write and create empty database if it does not exist)
            compression: Enable/disable FLAC compression data BLOBs for writing
        """
        super().__init__(
            filename, mode=mode, table_prefix="tr", required_file_ext=".tradb",
        )
        self._data_format = 2 if compression else 0
        self._timebase = self.globalinfo()["TimeBase"]

    @staticmethod
    def create(filename: str):
        """
        Create empty tradb.

        Args:
            filename: Path to new tradb database file
        """
        file_schema = Path(__file__).resolve().parent / "schema_templates/tradb.sql"
        with open(file_schema, "r", encoding="utf-8") as file:
            schema_tradb = file.read()
        schema_tradb = schema_tradb.format(timebase=int(1e7))  # fill placeholder / constants
        create_new_database(filename, schema_tradb)

    def channel(self) -> Set[int]:
        """Get list of channels."""
        con = self.connection()
        cur = con.execute("SELECT DISTINCT Chan FROM tr_data WHERE Chan IS NOT NULL")
        return {result[0] for result in cur.fetchall()}

    def read(self, **kwargs) -> pd.DataFrame:
        """
        Read transient data to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread`

        Returns:
            Pandas DataFrame with transient data
        """
        return iter_to_dataframe(
            self.iread(**kwargs), desc="Tra", index_column="trai",
        )

    def iread(
        self,
        *,
        channel: Union[None, int, Sequence[int]] = None,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        trai: Union[None, int, Sequence[int]] = None,
    ) -> SizedIterable[TraRecord]:
        """
        Stream transient data with returned Iterable.

        Args:
            channel: None if all channels should be read.
                Otherwise specify the channel number or a list of channel numbers
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            trai: Read data by TRAI (transient recorder index)

        Returns:
            Sized iterable to sequential read transient data
        """
        con = self.connection()
        setid_time_start = None
        setid_time_stop = None
        setid_max = con.execute(f"SELECT MAX(SetID) FROM {self._table_main}").fetchone()[0]

        if time_start is not None:
            setid_time_start = sql_binary_search(
                connection=con,
                table="view_tr_data",
                column_value="Time",
                column_index="SetID",
                fun_compare=lambda t: t >= time_start,  # type: ignore
                lower_bound=True,  # return lower index of true conditions
            )
        if time_stop is not None:
            setid_time_stop = sql_binary_search(
                connection=con,
                table="view_tr_data",
                column_value="Time",
                column_index="SetID",
                fun_compare=lambda t: t < time_stop,  # type: ignore
                lower_bound=False,  # return upper index of true conditions
            )

        # remove upper boundary if equal to max index
        # otherwise the last row is excluded (less condition)
        if setid_time_stop == setid_max:
            setid_time_stop = None

        query = """
        SELECT vtr.*, tr.ParamID
        FROM view_tr_data vtr
        LEFT JOIN tr_data tr ON vtr.SetID == tr.SetID
        """ + query_conditions(
            isin={"vtr.Chan": channel, "vtr.TRAI": trai},
            greater_equal={"vtr.SetID": setid_time_start},
            less={"vtr.SetID": setid_time_stop},
        )
        return QueryIterable(
            self._connection_wrapper.get_readonly_connection(),
            query,
            TraRecord.from_sql,
        )

    def read_wave(
        self, trai: int, time_axis: bool = True,
    ) -> Union[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, int]]:
        """
        Read transient signal for a given TRAI (transient recorder index).

        This method is useful in combination with `PriDatabase.read_hits`,
        that will store the TRAI in a DataFrame.

        Args:
            trai: Transient recorder index (unique key between pridb and tradb)
            time_axis: Create the correspondig time axis. Default: `True`

        Returns:
            If :attr:`time_axis` is `True`\n
            - Array with transient signal
            - Time axis

            If :attr:`time_axis` is `False`\n
            - Array with transient signal
            - Samplerate
        """
        iterable = self.iread(trai=trai)
        try:
            tra = next(iter(iterable))
        except StopIteration:
            raise ValueError("TRAI does not exists")

        if time_axis:
            return (
                tra.data,
                _create_time_vector(tra.samples, tra.samplerate, tra.pretrigger),
            )
        return tra.data, tra.samplerate

    def read_continuous_wave(
        self,
        channel: int,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        *,
        time_axis: bool = True,
        show_progress: bool = True,
    ) -> Union[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, int]]:
        """
        Read transient signal of specified channel to a single, continuous array.

        Time gaps are filled with 0's.

        Args:
            channel: Channel number to read
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            time_axis: Create the correspondig time axis. Default: `True`
            show_progress: Show progress bar. Default: `True`

        Returns:
            If `time_axis` is `True`\n
            - Array with transient signal
            - Time axis

            If `time_axis` is `False`\n
            - Array with transient signal
            - Samplerate
        """
        tra_blocks = [np.empty(0, dtype=np.float32)]
        sr = 0

        iterable = self.iread(channel=channel, time_start=time_start, time_stop=time_stop)
        iterator = iter(iterable)
        if show_progress:
            iterator = tqdm(iterator, total=len(iterable), desc="Tra")

        expected_time = None
        for tra in iterator:
            # check for gaps in tra stream
            if expected_time is not None:
                time_gap = tra.time - expected_time
                if time_gap > 1e-6:
                    samples_gap = round(time_gap * tra.samplerate)
                    tra_blocks.append(
                        np.zeros(samples_gap, dtype=np.float32)
                    )

            expected_time = tra.time + float(tra.samples) / tra.samplerate

            tra_blocks.append(tra.data)
            sr = tra.samplerate

        y = np.concatenate(tra_blocks)

        if time_axis:
            return y, _create_time_vector(len(y), sr)
        return y, sr

    @require_write_access
    def write(self, tra: TraRecord) -> int:
        """
        Write transient data to pridb.

        Args:
            tra: Transient data set

        Returns:
            Index (SetID) of inserted row

        Todo:
            Status flag
        """
        # self._validate_and_update_time(tra.time)
        parameter = self._parameter(tra.param_id)
        with self.connection() as con:  # commit/rollback transaction
            return insert_from_dict(
                con,
                self._table_main,
                {
                    "Time": int(tra.time * self._timebase),
                    "Chan": int(tra.channel),
                    "Status": 32768,
                    "ParamID": int(tra.param_id),
                    "Pretrigger": int(tra.pretrigger),
                    "Thr": int(tra.threshold * 1e6 / parameter["ADC_µV"]),
                    "SampleRate": int(tra.samplerate),
                    "Samples": int(tra.samples),
                    "DataFormat": int(self._data_format),
                    "Data": encode_data_blob(tra.data, self._data_format, parameter["TR_mV"]),
                    "TRAI": (
                        int(tra.trai)
                        if tra.trai else None
                    ),
                },
            )
