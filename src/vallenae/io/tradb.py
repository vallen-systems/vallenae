from __future__ import annotations

from functools import partial
from pathlib import Path
from time import sleep
from typing import Iterable, Sequence

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
    read_sql_generator,
    sql_binary_search,
)
from ._types import SizedIterable
from .compression import encode_data_blob
from .datatypes import TraRecord


def _create_time_vector(samples: int, samplerate: int, pretrigger: int = 0) -> np.ndarray:
    return np.arange(-pretrigger, samples - pretrigger, dtype=np.float32) / samplerate


class TraDatabase(Database):
    """IO wrapper for tradb database file."""

    def __init__(
        self,
        filename: str,
        mode: str = "ro",
        *,
        compression: bool = False,
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
            filename,
            mode=mode,
            table_prefix="tr",
            required_file_ext=".tradb",
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
        schema_path = Path(__file__).parent / "schema_templates/tradb.sql"
        schema = schema_path.read_text("utf-8").format(timebase=int(1e7))  # fill placeholder
        create_new_database(filename, schema)

    def channel(self) -> set[int]:
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
            self.iread(**kwargs),
            desc="Tra",
            index_column="trai",
        )

    def _get_total_time_range(self) -> tuple[float, float]:
        """Return total time range [first sample time, end of last sample] in seconds."""
        # view_tr_data.Time is already in seconds; the end of a record is
        # Time + Samples / SampleRate (the `* 1.0` forces float division).
        row = (
            self.connection()
            .execute("SELECT MIN(Time), MAX(Time + Samples * 1.0 / SampleRate) FROM view_tr_data")
            .fetchone()
        )
        if row is None or row[0] is None:  # empty table
            return 0.0, 0.0
        return row[0], row[1]

    def _get_trai_range_from_time_range(
        self, time_start: float | None, time_stop: float | None
    ) -> tuple[int | None, int | None]:
        """Binary-search the TRAI range of records overlapping a time range.

        Records have a duration, so the range includes the record straddling
        time_start (start <= time_start) and the record starting at time_stop.
        view_tr_data.Time is in seconds, so the conditions compare seconds directly.
        """
        search = partial(
            sql_binary_search,
            connection=self.connection(),
            table="view_tr_data",
            column_value="Time",
            column_index="TRAI",
        )
        trai_start = None
        trai_stop = None
        if time_start is not None:  # last record starting at/before time_start
            trai_start = search(fun_compare=lambda t: t <= time_start, lower_bound=False)
        if time_stop is not None:  # (first record starting after time_stop) - 1
            trai_after = search(fun_compare=lambda t: t > time_stop, lower_bound=True)
            trai_stop = None if trai_after is None else trai_after - 1
        return trai_start, trai_stop

    def iread(
        self,
        *,
        channel: int | Sequence[int] | None = None,
        time_start: float | None = None,
        time_stop: float | None = None,
        trai: int | Sequence[int] | None = None,
        query_filter: str | None = None,
        raw: bool = False,
    ) -> SizedIterable[TraRecord]:
        """
        Stream transient data with returned Iterable.

        Args:
            channel: None if all channels should be read.
                Otherwise specify the channel number or a list of channel numbers
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            trai: Read data by TRAI (transient recorder index)
            query_filter: Optional query filter provided as SQL clause,
                e.g. "Pretrigger == 500 AND Samples >= 1024"
            raw: Return data as ADC values (int16). Default: `False`

        Returns:
            Sized iterable to sequential read transient data
        """
        # check for empty time ranges (time_max is the end of the last sample, exclusive)
        time_min, time_max = self._get_total_time_range()
        if time_start is not None and time_start >= time_max:
            return []
        if time_stop is not None and time_stop < time_min:
            return []
        if time_start is not None and time_stop is not None and time_start >= time_stop:
            return []

        trai_start, trai_stop = self._get_trai_range_from_time_range(time_start, time_stop)
        # nested query to fix ambiguous column name error with query_filter
        query = """
        SELECT * FROM (
            SELECT vtr.*, tr.ParamID
            FROM view_tr_data vtr
            LEFT JOIN tr_data tr ON vtr.SetID == tr.SetID
            ORDER BY TRAI ASC
        )
        """ + query_conditions(
            isin={"Chan": channel, "TRAI": trai},
            greater_equal={"TRAI": trai_start},
            # trai_start/trai_stop are inclusive bounds from the binary search
            less_equal={"TRAI": trai_stop},
            custom_filter=query_filter,
        )
        return QueryIterable(
            self._connection_wrapper.get_readonly_connection(),
            query,
            partial(TraRecord.from_sql, raw=raw),
        )

    def read_wave(
        self,
        trai: int,
        time_axis: bool = True,
        *,
        raw: bool = False,
    ) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, int]:
        """
        Read transient signal for a given TRAI (transient recorder index).

        This method is useful in combination with `PriDatabase.read_hits`,
        that will store the TRAI in a DataFrame.

        Args:
            trai: Transient recorder index (unique key between pridb and tradb)
            time_axis: Create the correspondig time axis. Default: `True`
            raw: Return data as ADC values (int16). Default: `False`

        Returns:
            If :attr:`time_axis` is `True`\n
            - Array with transient signal
            - Time axis

            If :attr:`time_axis` is `False`\n
            - Array with transient signal
            - Samplerate
        """
        iterable = self.iread(trai=trai, raw=raw)
        try:
            tra = next(iter(iterable))
        except StopIteration:
            raise ValueError("TRAI does not exists") from None

        if time_axis:
            return (
                tra.data,
                _create_time_vector(tra.samples, tra.samplerate, tra.pretrigger),
            )
        return tra.data, tra.samplerate

    def read_continuous_wave(
        self,
        channel: int,
        time_start: float | None = None,
        time_stop: float | None = None,
        *,
        time_axis: bool = True,
        show_progress: bool = True,
        raw: bool = False,
    ) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, int]:
        """
        Read transient signal of specified channel to a single, continuous array.

        The signal is exactly cropped to the given time range. Time gaps are filled with 0's.

        A single sample rate per channel is assumed: the sample rate of the channel's first
        record is used. A record with a differing sample rate inside the requested range
        raises a `RuntimeError`.

        Args:
            channel: Channel number to read
            time_start: Start reading at relative time (in seconds). Start at beginning if `None`
            time_stop: Stop reading at relative time (in seconds). Read until end if `None`
            time_axis: Create the correspondig time axis. Default: `True`
            show_progress: Show progress bar. Default: `True`
            raw: Return data as ADC values (int16). Default: `False`

        Returns:
            If `time_axis` is `True`\n
            - Array with transient signal
            - Time axis

            If `time_axis` is `False`\n
            - Array with transient signal
            - Samplerate
        """
        dtype = np.int16 if raw else np.float32
        con = self.connection()

        # Assume a uniform sample rate per channel; take the first record's.
        # Indexed LIMIT 1 lookup - avoids scanning every row (e.g. DISTINCT SampleRate would).
        row = con.execute(
            "SELECT SampleRate FROM view_tr_data WHERE Chan == ? ORDER BY TRAI LIMIT 1", (channel,)
        ).fetchone()
        if row is None:  # no data for this channel
            empty = np.empty(0, dtype=dtype)
            return (empty, np.empty(0, dtype=np.float32)) if time_axis else (empty, 0)
        samplerate = row[0]

        if time_start is None or time_stop is None:  # fill open bounds from channel extent
            extent = con.execute(
                "SELECT MIN(Time), MAX(Time + Samples * 1.0 / SampleRate) "
                "FROM view_tr_data WHERE Chan == ?",
                (channel,),
            ).fetchone()
            if time_start is None:
                time_start = extent[0]
            if time_stop is None:
                time_stop = extent[1]

        iterable = self.iread(channel=channel, time_start=time_start, time_stop=time_stop, raw=raw)
        iterator = iter(iterable)
        if show_progress:
            iterator = tqdm(iterator, total=len(iterable), desc="Tra")

        sample_start = round(time_start * samplerate)
        sample_stop = round(time_stop * samplerate)
        num_samples = max(0, sample_stop - sample_start)
        y = np.zeros(num_samples, dtype=dtype)

        for tra in iterator:
            if tra.samplerate != samplerate:  # safety net for the uniform-rate assumption
                raise RuntimeError("Different sampling rates inside requested time interval")
            tra_start = round(tra.time * samplerate)
            n = len(tra.data)
            # overlapping slice of [sample_start, sample_stop) with this record's [tra_start, +n)
            src_lo = max(0, sample_start - tra_start)
            src_hi = min(n, sample_stop - tra_start)
            if src_hi > src_lo:
                dst_lo = max(0, tra_start - sample_start)
                y[dst_lo : dst_lo + (src_hi - src_lo)] = tra.data[src_lo:src_hi]

        if time_axis:
            return y, _create_time_vector(num_samples, samplerate) + time_start
        return y, samplerate

    def listen(
        self,
        existing: bool = False,
        wait: bool = False,
        query_filter: str | None = None,
        raw: bool = False,
    ) -> Iterable[TraRecord]:
        """
        Listen to database changes and return new records.

        Args:
            existing: Return already existing records
            wait: Wait for new records even if no acquisition (writer) is active.
                Otherwise the function returns after all records are read.
            query_filter: Optional query filter provided as SQL clause,
                e.g. "TRAI >= 100 AND Samples >= 1024"
            raw: Return data as ADC values (int16). Default: `False`

        Yields:
            New transient data records
        """
        max_buffer_size = 100
        query = f"""
        SELECT * FROM (
            SELECT vtr.*, tr.ParamID
            FROM view_tr_data vtr
            LEFT JOIN tr_data tr ON vtr.SetID == tr.SetID
            WHERE vtr.SetID > ?
        ) {query_conditions(custom_filter=query_filter)} LIMIT {max_buffer_size}
        """
        last_set_id = 0 if existing else self._main_index_range()[1]
        while True:
            # buffer rows to allow in-between write transactions
            rows = list(read_sql_generator(self.connection(), query, last_set_id))
            for row in rows:
                yield TraRecord.from_sql(row, raw=raw)
                last_set_id = row["SetID"]
            if len(rows) == 0:
                if not wait and self._file_status() == 0:  # no writer active
                    break
                sleep(0.1)  # wait 100 ms until next read

    @require_write_access
    def write(self, tra: TraRecord) -> int:
        """
        Write transient data to pridb.

        Args:
            tra: Transient data set

        Returns:
            Index (SetID) of inserted row
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
                    "Status": tra.status,
                    "ParamID": int(tra.param_id),
                    "Pretrigger": int(tra.pretrigger),
                    "Thr": int(tra.threshold * 1e6 / parameter["ADC_µV"]),
                    "SampleRate": int(tra.samplerate),
                    "Samples": int(tra.samples),
                    "DataFormat": int(self._data_format),
                    "Data": encode_data_blob(tra.data, self._data_format, parameter["TR_mV"]),
                    "TRAI": int(tra.trai) if tra.trai is not None else None,
                },
            )
