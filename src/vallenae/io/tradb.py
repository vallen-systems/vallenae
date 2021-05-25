from functools import lru_cache
from itertools import chain
from pathlib import Path
from time import sleep
from typing import Iterable, Optional, Sequence, Set, Tuple, Union

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
from .compression import encode_data_blob
from .datatypes import TraRecord
from .types import SizedIterable


@lru_cache(maxsize=32, typed=True)
def _create_time_vector(
    samples: int, samplerate: int, pretrigger: int = 0
) -> np.ndarray:
    return np.arange(-pretrigger, samples - pretrigger, dtype=np.float32) / samplerate


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

    def _get_total_time_range(self) -> Tuple[float, float]:
        """Return total time range [min, max] of tradb."""
        def get_time(func: str):
            result = self.connection().execute(
                f"SELECT Time FROM tr_data WHERE TRAI == (SELECT {func}(TRAI) from tr_data)"
            ).fetchone()
            return 0 if result is None else result[0] / self._timebase
        return get_time("MIN"), get_time("MAX")

    def _get_trai_range_from_time_range(
        self, time_start: Optional[float], time_stop: Optional[float]
    ) -> Tuple[Optional[int], Optional[int]]:
        """Use binary search to find indexes (TRAI) of a given time range."""
        con = self.connection()
        trai_start = None
        trai_stop = None
        if time_start is not None:
            trai_start = sql_binary_search(
                connection=con,
                table="tr_data",
                column_value="Time",
                column_index="TRAI",
                fun_compare=lambda t: t >= time_start * self._timebase,  # type: ignore
                lower_bound=True,  # return lower index of true conditions
            )
        if time_stop is not None:
            trai_stop = sql_binary_search(
                connection=con,
                table="tr_data",
                column_value="Time",
                column_index="TRAI",
                fun_compare=lambda t: t < time_stop * self._timebase,  # type: ignore
                lower_bound=False,  # return upper index of true conditions
            )
        return trai_start, trai_stop

    def iread(
        self,
        *,
        channel: Union[None, int, Sequence[int]] = None,
        time_start: Optional[float] = None,
        time_stop: Optional[float] = None,
        trai: Union[None, int, Sequence[int]] = None,
        query_filter: Optional[str] = None,
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

        Returns:
            Sized iterable to sequential read transient data
        """
        # check for empty time ranges
        time_min, time_max = self._get_total_time_range()
        if time_start is not None:
            if time_start > time_max:
                return []
        if time_stop is not None:
            if time_stop < time_min:
                return []
        if time_start is not None and time_stop is not None:
            if time_start >= time_stop:
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
            # < condition already met in binary search, use <= here for found indice range
            less_equal={"TRAI": trai_stop},
            custom_filter=query_filter,
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
            raise ValueError("TRAI does not exists") from None

        if time_axis:
            return (
                tra.data,
                _create_time_vector(tra.samples, tra.samplerate, tra.pretrigger),
            )
        return tra.data, tra.samplerate

    def _get_previous_trai(self, channel: int, trai: int) -> Optional[int]:
        """Find previous tra record index for given channel and TRAI."""
        result = self.connection().execute(
            "SELECT TRAI FROM tr_data WHERE Chan == ? AND TRAI < ? ORDER BY TRAI DESC LIMIT 1",
            (channel, trai),
        ).fetchone()
        return result[0] if result is not None else None

    def read_continuous_wave(  # pylint: disable=too-many-locals
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

        The signal is exactly cropped to the given time range. Time gaps are filled with 0's.

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
        iterable = self.iread(channel=channel, time_start=time_start, time_stop=time_stop)
        iterator = iter(iterable)
        if show_progress:
            iterator = tqdm(iterator, total=len(iterable), desc="Tra")  # ignores previous tra

        # prepend previous tra to iterator if available
        trai_start, _ = self._get_trai_range_from_time_range(time_start, None)
        if trai_start is not None:
            previous_trai = self._get_previous_trai(channel, trai_start)
            if previous_trai is not None:
                iterator = chain(
                    iter(self.iread(channel=channel, trai=previous_trai)),
                    iterator,
                )

        # find beginning if not provided
        if time_start is None:
            time_start = self._get_total_time_range()[0]

        def slice_range(tra: TraRecord):
            """Get indices to slice given tra record data to time range."""
            def limit_index(i: int):
                return min(max(0, i), tra.samples)
            n_start, n_stop = 0, tra.samples
            if time_start is not None:
                n_start = limit_index(round((time_start - tra.time) * tra.samplerate))
            if time_stop is not None:
                n_stop = limit_index(round((time_stop - tra.time) * tra.samplerate))
            return n_start, n_stop

        samplerate = 0  # will be initialized with samplerate of first record
        tra_blocks = [np.empty(0, dtype=np.float32)]
        expected_time = time_start

        for tra in iterator:
            if samplerate == 0:
                samplerate = tra.samplerate
            if tra.samplerate != samplerate:
                raise RuntimeError("Different sampling rates inside requested time interval")

            # check for gaps in tra stream
            time_gap = tra.time - expected_time
            if time_gap > 1 / tra.samplerate:
                samples_gap = round(time_gap * tra.samplerate)
                tra_blocks.append(np.zeros(samples_gap, dtype=np.float32))

            sample_start, sample_stop = slice_range(tra)
            tra_blocks.append(tra.data[sample_start:sample_stop])
            expected_time = tra.time + sample_stop / tra.samplerate
            if time_start is not None:
                # the prepended record might be out of time range -> avoid exceeding zero-padding
                expected_time = max(expected_time, time_start)

        if time_stop is not None and samplerate and abs(expected_time - time_stop) > 1 / samplerate:
            # zero padding at ending
            samples = round((time_stop - expected_time) * samplerate)
            tra_blocks.append(np.zeros(samples, dtype=np.float32))

        y = np.concatenate(tra_blocks)
        if time_axis:
            return y, _create_time_vector(len(y), samplerate) + time_start
        return y, samplerate

    def listen(
        self,
        existing: bool = False,
        wait: bool = False,
        query_filter: Optional[str] = None,
    ) -> Iterable[TraRecord]:
        """
        Listen to database changes and return new records.

        Args:
            existing: Return already existing records
            wait: Wait for new records even if no acquisition (writer) is active.
                Otherwise the function returns after all records are read.
            query_filter: Optional query filter provided as SQL clause,
                e.g. "TRAI >= 100 AND Samples >= 1024"

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
                yield TraRecord.from_sql(row)
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
