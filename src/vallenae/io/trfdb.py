from typing import Union, Sequence
import pandas as pd

from .types import SizedIterable
from .datatypes import FeatureRecord
from ._database import Database
from ._sql import query_conditions, QueryIterable


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
        return pd.read_sql(query, self.connection(), index_col="TRAI")

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
