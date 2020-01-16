from pathlib import Path
from typing import Union, Sequence
import sqlite3
import pandas as pd

from .types import SizedIterable
from .datatypes import FeatureRecord
from ._database import Database, require_write_access
from ._sql import (
    query_conditions,
    QueryIterable,
    insert_from_dict,
    update_from_dict,
    create_new_database,
)


class TrfDatabase(Database):
    """IO Wrapper for trfdb (transient feature) database file."""

    def __init__(
        self, filename: str, *, readonly: bool = True,
    ):
        """
        Open trfdb database file.

        Args:
            filename: Path to trfdb database file
            readonly: Open database in read-only mode (`True`) or read-write mode (`False`)
        """
        super().__init__(
            filename, table_prefix="trf", readonly=readonly, required_file_ext="trfdb",
        )

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
        return QueryIterable(self.connection(), query, FeatureRecord.from_sql)

    @require_write_access
    def write(self, feature_set: FeatureRecord) -> int:
        """
        Write feature record to trfdb.

        Args:
            feature_set: Feature set

        Returns:
            Index (trai) of inserted row
        """
        con = self.connection()
        row_dict = feature_set.features
        row_dict["TRAI"] = feature_set.trai
        try:
            try:
                return insert_from_dict(con, self._table_main, row_dict)
            except sqlite3.IntegrityError:  # UNIQUE constraint, TRAI already exists
                # update instead
                return update_from_dict(con, self._table_main, row_dict, "TRAI")
        except sqlite3.OperationalError:  # missing column
            columns_expected = set(row_dict.keys())
            columns_create = columns_expected - set(self.columns())
            for column in columns_create:
                con.execute(f"ALTER TABLE {self._table_main} ADD COLUMN {column} REAL")
            return self.write(feature_set)  # try again


def create_empty_trfdb(filename: str):
    file_schema = Path(__file__).resolve().parent / "schema_templates/trfdb.sql"
    with open(file_schema, "r") as file:
        schema = file.read()
    create_new_database(filename, schema)
