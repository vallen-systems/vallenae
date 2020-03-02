import sqlite3
from pathlib import Path
from typing import Sequence, Union

import pandas as pd

from ._database import Database, require_write_access
from ._sql import (
    QueryIterable,
    create_new_database,
    insert_from_dict,
    query_conditions,
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

    def read(
        self, *, trai: Union[None, int, Sequence[int]] = None
    ) -> pd.DataFrame:
        """
        Read features to Pandas DataFrame.

        Args:
            trai: Read data by TRAI (transient recorder index)

        Returns:
            Pandas DataFrame with features
        """
        query = "SELECT * FROM trf_data " + query_conditions(isin={"TRAI": trai})
        df = pd.read_sql(query, self.connection(), index_col="TRAI")
        df.index.name = "trai"  # TRAI -> trai, as with pridb and tradb
        return df

    def iread(
        self, *, trai: Union[None, int, Sequence[int]] = None
    ) -> SizedIterable[FeatureRecord]:
        """
        Stream features with returned iterable.

        Args:
            trai: Read data by TRAI (transient recorder index)

        Returns:
            Sized iterable to sequential read features
        """
        query = "SELECT * FROM trf_data " + query_conditions(isin={"TRAI": trai})
        return QueryIterable(
            self._connection_wrapper.get_readonly_connection(),
            query,
            FeatureRecord.from_sql,
        )

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
