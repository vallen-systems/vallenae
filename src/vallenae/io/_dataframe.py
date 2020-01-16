from typing import Optional, Tuple
import pandas as pd
from numpy import int32, int64
from tqdm import tqdm

from .types import SizedIterable


def convert_to_nullable_types(df: pd.DataFrame):
    df_convert = df

    def convert_column(column, dtype):
        df_convert[column] = df_convert[column].astype(dtype)

    for name, dtype in dict(df.dtypes).items():
        if dtype == int32:
            convert_column(name, pd.Int32Dtype())
        elif dtype == int64:
            convert_column(name, pd.Int64Dtype())

    return df_convert


def iter_to_dataframe(
    iterable: SizedIterable[Tuple],
    show_progress: bool = True,
    desc: str = "",
    index_column: Optional[str] = None,
) -> pd.DataFrame:
    """
    Helper function to save iterator results in Pandas DataFrame.

    Args:
        iterable: Iterable generating `NamedTuple`s
        show_progress: Show progress bar. Default: `True`
        desc: Description shown left to the progress bar
    Returns:
        Pandas DataFrame
    """
    iterator = iter(iterable)
    if show_progress:
        iterator = tqdm(iterator, total=len(iterable), desc=desc)
    df = pd.DataFrame(iterator)
    if not df.empty:
        df = df.dropna(axis="columns", how="all")  # drop empty columns
        if index_column is not None:
            df = df.set_index(index_column)
    df = convert_to_nullable_types(df)
    return df
