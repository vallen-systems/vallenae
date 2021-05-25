import sqlite3
from pathlib import Path
from time import sleep
from typing import Iterable, Optional, Sequence, Union

import pandas as pd

from ._database import Database, require_write_access
from ._dataframe import iter_to_dataframe
from ._sql import (
    QueryIterable,
    create_new_database,
    insert_from_dict,
    query_conditions,
    read_sql_generator,
    update_from_dict,
)
from .datatypes import FeatureRecord
from .types import SizedIterable


class TrfDatabase(Database):
    """IO Wrapper for trfdb (transient feature) database file."""

    def __init__(self, filename: str, mode: str = "ro"):
        """
        Open trfdb database file.

        Args:
            filename: Path to trfdb database file
            mode: Define database access:
                **"ro"** (read-only),
                **"rw"** (read-write),
                **"rwc"** (read-write and create empty database if it does not exist)
        """
        super().__init__(
            filename, mode=mode, table_prefix="trf", required_file_ext=".trfdb",
        )

    @staticmethod
    def create(filename: str):
        """
        Create empty trfdb.

        Args:
            filename: Path to new trfdb database file
        """
        file_schema = Path(__file__).resolve().parent / "schema_templates/trfdb.sql"
        with open(file_schema, "r", encoding="utf-8") as file:
            schema_trfdb = file.read()
        create_new_database(filename, schema_trfdb)

    def read(self, **kwargs) -> pd.DataFrame:
        """
        Read features to Pandas DataFrame.

        Args:
            **kwargs: Arguments passed to `iread`

        Returns:
            Pandas DataFrame with features
        """
        def record_to_dict(record: FeatureRecord):
            return dict(trai=record.trai, **record.features)
        return iter_to_dataframe(
            [record_to_dict(r) for r in self.iread(**kwargs)], desc="Trf", index_column="trai",
        )

    def iread(
        self,
        *,
        trai: Union[None, int, Sequence[int]] = None,
        query_filter: Optional[str] = None,
    ) -> SizedIterable[FeatureRecord]:
        """
        Stream features with returned iterable.

        Args:
            trai: Read data by TRAI (transient recorder index)
            query_filter: Optional query filter provided as SQL clause,
                e.g. "FFT_CoG >= 150 AND CTP < 20"

        Returns:
            Sized iterable to sequential read features
        """
        query = """
        SELECT * FROM (
            SELECT * FROM trf_data
            ORDER BY TRAI ASC
        )
        """ + query_conditions(isin={"TRAI": trai}, custom_filter=query_filter)
        return QueryIterable(
            self._connection_wrapper.get_readonly_connection(),
            query,
            FeatureRecord.from_sql,
        )

    def listen(
        self,
        existing: bool = False,
        wait: bool = False,
        query_filter: Optional[str] = None,
    ) -> Iterable[FeatureRecord]:
        """
        Listen to database changes and return new records.

        Args:
            existing: Return already existing records
            wait: Wait for new records even if no acquisition (writer) is active.
                Otherwise the function returns after all records are read.
            query_filter: Optional query filter provided as SQL clause,
                e.g. "TRAI >= 100"

        Yields:
            New feature records
        """
        max_buffer_size = 1000
        query = f"""
        SELECT * FROM (
            SELECT rowid, * FROM trf_data
            WHERE rowid > ?
        ) {query_conditions(custom_filter=query_filter)} LIMIT {max_buffer_size}
        """
        last_rowid = 0 if existing else self._main_index_range()[1]
        while True:
            # buffer rows to allow in-between write transactions
            rows = list(read_sql_generator(self.connection(), query, last_rowid))
            for row in rows:
                last_rowid = row.pop("rowid")
                yield FeatureRecord.from_sql(row)
            if len(rows) == 0:
                if not wait and self._file_status() == 0:  # no writer active
                    break
                sleep(0.1)  # wait 100 ms until next read

    @require_write_access
    def write(self, feature_set: FeatureRecord) -> int:
        """
        Write feature record to trfdb.

        Args:
            feature_set: Feature set

        Returns:
            Index (trai) of inserted row
        """
        def convert(value):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        with self.connection() as con:  # commit/rollback transaction
            row_dict = {
                key: convert(value)
                for key, value in feature_set.features.items()
            }
            row_dict["TRAI"] = feature_set.trai
            try:
                try:
                    return insert_from_dict(con, self._table_main, row_dict)
                except sqlite3.IntegrityError:  # UNIQUE constraint, TRAI already exists
                    # update instead
                    return update_from_dict(con, self._table_main, row_dict, "TRAI")
            except sqlite3.OperationalError:  # missing column(s)
                self._add_columns(self._table_main, list(row_dict.keys()), "REAL")
                return self.write(feature_set)  # try again
