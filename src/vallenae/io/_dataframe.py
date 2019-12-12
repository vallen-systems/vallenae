from typing import Optional, Tuple
import pandas as pd
from tqdm import tqdm

from .types import SizedIterable


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
    return df
