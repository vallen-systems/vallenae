import pandas as pd
from numpy import dtype
from vallenae.io._dataframe import _convert_to_nullable_types


def test_convert_to_nullable_types():
    x = list(range(10))

    df = pd.DataFrame({
        "int32": pd.Series(x, dtype="int32"),
        "int64": pd.Series(x, dtype="int64"),
        "float": pd.Series(x, dtype="float64"),
        "bool": pd.Series(x, dtype=bool),
    })

    assert list(df.dtypes) == [
        dtype("int32"),
        dtype("int64"),
        dtype("float64"),
        dtype("bool"),
    ]

    df_converted = _convert_to_nullable_types(df)

    assert list(df_converted.dtypes) == [
        pd.Int32Dtype(),
        pd.Int64Dtype(),
        dtype("float64"),
        dtype("bool"),
    ]
