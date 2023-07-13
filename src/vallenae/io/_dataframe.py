from typing import Optional, Tuple

import pandas as pd
from tqdm import tqdm

from .types import SizedIterable


def _convert_to_nullable_types(df: pd.DataFrame):
    # types not hashable -> use str repr
    dtype_mapping = {
        "int32": pd.Int32Dtype(),
        "int64": pd.Int64Dtype(),
    }
    return df.apply(
        lambda x: x.astype(
            dtype_mapping.get(
                str(x.dtype),  # try get new dtype
                x.dtype,  # return original dtype if key not found
            )
        )
    )


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
        index_column: Set column as index. Default: `None`
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
    return _convert_to_nullable_types(df)
