from typing import Set, Optional, Union, Tuple, Sequence
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

from ._database import Database, require_write_access
from ._dataframe import iter_to_dataframe
from ._sql import (
    QueryIterable,
    query_conditions,
    sql_binary_search,
    insert_from_dict,
    create_new_database,
)
from .compression import encode_data_blob
from .datatypes import TraRecord
from .types import SizedIterable
from .._cache import cache


@cache()
def _create_time_vector(
    samples: int, samplerate: int, pretrigger: int = 0
) -> np.ndarray:
    t_raw = np.arange(-pretrigger, samples - pretrigger, dtype=np.int32)
    t_scaled = (t_raw / np.float32(samplerate)).astype(np.float32)
    return t_scaled


class TraDatabase(Database):
    """IO Wrapper for tradb database file."""

    def __init__(
        self, filename: str, *, readonly: bool = True, compression: bool = False,
    ):
        """
        Open tradb database file.

        Args:
            filename: Path to tradb database file
            readonly: Open database in read-only mode (`True`) or read-write mode (`False`)
            compression: Enable/disable FLAC compression data BLOBs for writing
        """
        super().__init__(
            filename, table_prefix="tr", readonly=readonly, required_file_ext="tradb",
        )
        self._data_format = 2 if compression else 0
        self._timebase = self.globalinfo()["TimeBase"]

    def channel(self) -> Set[int]:
        """Get list of channels."""
        con = self.connection()
        cur = con.execute("SELECT DISTINCT Chan FROM tr_data WHERE Chan IS NOT NULL")
        return {result[0] for result in cur.fetchall()}

    def read(self, **kwargs) -> pd.DataFrame:
        """
        Read hits to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread`
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

        if time_start is not None:
            setid_time_start = sql_binary_search(
                con, "view_tr_data", "Time", "SetID", lambda t: t >= time_start  # type: ignore
            )
        if time_stop is not None:
            setid_time_stop = sql_binary_search(
                con, "view_tr_data", "Time", "SetID", lambda t: t < time_stop  # type: ignore
            )

        query = """
        SELECT vtr.*, tr.ParamID
        FROM view_tr_data vtr
        LEFT JOIN tr_data tr ON vtr.SetID == tr.SetID
        """ + query_conditions(
            isin={"vtr.Chan": channel, "vtr.TRAI": trai},
            greater_equal={"vtr.SetID": setid_time_start},
            less={"vtr.SetID": setid_time_stop},
        )
        return QueryIterable(con, query, TraRecord.from_sql)

    def read_wave(
        self, trai: int, time_axis: bool = True,
    ) -> Union[Tuple[np.ndarray, np.ndarray], np.ndarray]:
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
        *,
        time_axis: bool = True,
        show_progress: bool = True,
        **kwargs,
    ) -> Union[Tuple[np.ndarray, np.ndarray], np.ndarray]:
        """
        Read transient signal of specified channel to a single, continuous array.

        Time gaps are filled with 0's.

        Args:
            channel: Channel number to be read
            time_axis: Create the correspondig time axis. Default: `True`
            show_progress: Show progress bar. Default: `True`
            **kwargs: Additional arguments passed to `~.iread`

        Returns:
            If `time_axis` is `True`\n
            - Array with transient signal
            - Time axis

            If `time_axis` is `False`\n
            - Array with transient signal
            - Samplerate
        """
        tra_blocks = [np.empty(0)]
        sr = 0

        iterable = self.iread(channel=channel, **kwargs)
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
                    tra_blocks.append(np.zeros(samples_gap))

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
        """
        # self._validate_and_update_time(tra.time)
        parameter = self._parameter(tra.param_id)
        return insert_from_dict(
            self.connection(),
            self._table_main,
            {
                "Time": int(tra.time * self._timebase),
                "Chan": tra.channel,
                "Status": 32768,
                "ParamID": tra.param_id,
                "Pretrigger": tra.pretrigger,
                "Thr": int(tra.threshold * 1e6 / parameter["ADC_µV"]),
                "SampleRate": tra.samplerate,
                "Samples": tra.samples,
                "DataFormat": self._data_format,
                "Data": encode_data_blob(tra.data, self._data_format, parameter["TR_mV"]),
                "TRAI": tra.trai,
            },
        )


def create_empty_tradb(filename: str):
    file_schema = Path(__file__).resolve().parent / "schema_templates/tradb.sql"
    with open(file_schema, "r") as file:
        schema = file.read()
    schema = schema.format(timebase=int(1e7))  # fill placeholder / constants
    create_new_database(filename, schema)