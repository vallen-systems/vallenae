import contextlib
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Sequence, Tuple, TypeVar, Union

from .types import SizedIterable

T = TypeVar("T")
class QueryIterable(SizedIterable[T]):
    """Sized iterable to query results from SQLite as dictionaries."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        query: str,
        dict_to_type: Callable[[Dict[str, Any]], T],
    ):
        self._connection = connection
        self._query = query
        self._dict_to_type = dict_to_type

    def __len__(self) -> int:
        return count_sql_results(self._connection, self._query)

    def __iter__(self) -> Iterator[T]:
        for row in read_sql_generator(self._connection, self._query):
            yield self._dict_to_type(row)


TIsIn = Dict[str, Union[float, Sequence[float], None]]
TComparison = Dict[str, Optional[float]]


def query_conditions(
    *,
    isin: Optional[TIsIn] = None,
    equal: Optional[TComparison] = None,
    less: Optional[TComparison] = None,
    less_equal: Optional[TComparison] = None,
    greater: Optional[TComparison] = None,
    greater_equal: Optional[TComparison] = None,
) -> str:
    cond = []

    if isin is not None:
        for key, values in isin.items():
            if values is None:
                continue
            if not isinstance(values, Sequence):
                values = (values,)
            cond.append(
                "{:s} IN ({:s})".format(key, ", ".join(str(value) for value in values))
            )

    comparison = {
        "==": equal,
        "<": less,
        "<=": less_equal,
        ">": greater,
        ">=": greater_equal,
    }

    for comp_operator, comp_dict in comparison.items():
        if comp_dict is not None:
            for key, value in comp_dict.items():
                if value is None:
                    continue
                if isinstance(value, str):
                    value = f"'{value}'"  # add quotation marks
                cond.append(f"{key} {comp_operator} {value}")

    return "WHERE " + " AND ".join(cond) if cond else ""


def read_sql_generator(
    connection: sqlite3.Connection, query: str
) -> Iterator[Dict[str, Any]]:
    """
    Generator to query data from a SQLite connection as a dictionary.

    Args:
        connection: SQLite3 connection object
        query: SELECT Query

    Yields:
        Row of the query result set as namedtuple
    """
    cur = connection.execute(query)
    columns = [column[0] for column in cur.description]

    while True:
        values = cur.fetchone()
        if values is None:
            break
        yield dict(zip(columns, values))


def count_sql_results(connection: sqlite3.Connection, query: str) -> int:
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cur = connection.execute(count_query)
    return cur.fetchone()[0]


def sql_binary_search(
    connection: sqlite3.Connection,
    table: str,
    column_value: str,
    column_index: str,
    fun_compare: Callable[[float], bool],
) -> Optional[int]:
    """
    Helper function to find the boundary row-index for given condition on a sorted column.

    Especially using conditions on the pridb's and tradb's Time column are expensive (not indexed).
    E.g.: SELECT * FROM view_tr_data WHERE Time > 10 AND Time < 100
    Because the Time column is monotonic increasing, a fast binary search can be applied.

    Args:
        connection: SQLite connection
        table: Table name
        column_value: Name of the sorted column, e.g. Time
        column_index: Name of the indexed column
        fun_compare: Lambda function of the condition, e.g. `lambda t: t > 10` (Time > 10)
    """

    def get_value(index):
        cur = connection.execute(
            f"SELECT {column_value} FROM {table} WHERE {column_index} == {index}"
        )
        return cur.fetchone()[0]

    i_min = connection.execute(
        f"SELECT MIN({column_index}) FROM {table}"
    ).fetchone()[0]
    i_max = connection.execute(
        f"SELECT MAX({column_index}) FROM {table}"
    ).fetchone()[0]

    while True:
        v_min = get_value(i_min)
        v_max = get_value(i_max)
        if v_min > v_max:
            raise ValueError(f"Value column {column_value} not sorted")
        c_min = fun_compare(v_min)
        c_max = fun_compare(v_max)

        if c_min and c_max:
            return i_min  # condition true for both limits, return smaller index
        if not c_min and not c_max:
            return None  # condition false for both limits

        if i_max - i_min < 2:
            return i_min if c_min is True else i_max

        i_mid = (i_max + i_min) // 2
        c_mid = fun_compare(get_value(i_mid))

        if c_mid == c_min:
            i_min = i_mid
        else:
            i_max = i_mid


def create_new_database(filename: str, schema: str):
    if Path(filename).resolve().exists():
        raise ValueError("Can not create new database. File already exists")

    # open database in read-write-create mode
    with contextlib.closing(
        sqlite3.connect(f"file:{filename}?mode=rwc", uri=True)
    ) as con:
        con.executescript(schema)


def remove_none_values_from_dict(dictionary: Dict[Any, Any]):
    """Helper function to remove None values from dict."""
    return {k: v for k, v in dictionary.items() if v is not None}


@lru_cache(maxsize=128, typed=True)
def generate_insert_query(table: str, columns: Tuple[str, ...]) -> str:
    """
    Generate INSERT query with named placeholders.

    e.g.: INSERT INTO ae_data (SetID, Time, Channel) VALUES (:SetID, :Time, :Channel)

    Args:
        table: Table name
        columns: Tuple of column names
            (must be of type tuple to be hashable for caching)

    Returns:
        Query string with named placeholders
    """
    query = "INSERT INTO {table} ({columns}) VALUES ({placeholder})".format(
        table=table,
        columns=", ".join(columns),
        placeholder=", ".join([":" + col for col in columns]),
    )
    return query


def insert_from_dict(
    connection: sqlite3.Connection,
    table: str,
    row_dict: Dict[str, Any],
) -> int:
    """INSERT row for given dict of column names -> values in SQLite table."""
    row_dict = remove_none_values_from_dict(row_dict)
    columns = tuple(row_dict.keys())
    query = generate_insert_query(table, columns)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid


@lru_cache(maxsize=128, typed=True)
def generate_update_query(table: str, columns: Tuple[str, ...], key_column: str) -> str:
    """
    Generate UPDATE query with named placeholders.

    e.g.: UPDATE ae_data SET Time = :Time, Channel = :Channel WHERE SetID == :SetID

    Args:
        table: Table name
        columns: Tuple of column names
            (must be of type tuple to be hashable for caching)
        key_column: Column name for WHERE clause

    Returns:
        Query string with named placeholders
    """
    columns_list = list(columns)
    try:
        columns_list.remove(key_column)
    except ValueError:
        raise ValueError(f"Argument key_column '{key_column}' must be a key of row_dict")

    query = "UPDATE {table} SET {set} WHERE {condition}".format(
        table=table,
        set=", ".join([f"{col} = :{col}" for col in columns_list]),
        condition=f"{key_column} == :{key_column}",
    )
    return query


def update_from_dict(
    connection: sqlite3.Connection,
    table: str,
    row_dict: Dict[str, Any],
    key_column: str,
) -> int:
    """UPDATE row for given key and dict of column names -> values in SQLite table."""
    row_dict = remove_none_values_from_dict(row_dict)
    columns = tuple(row_dict.keys())
    query = generate_update_query(table, columns, key_column)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid
