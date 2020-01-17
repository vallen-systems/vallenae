import contextlib
import sqlite3
from typing import Dict, Optional, Union, Sequence, Iterator, Any, TypeVar, Callable
from pathlib import Path

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


def query_conditions(
    *,
    isin: Dict[str, Union[float, Sequence[float], None]] = {},
    equal: Dict[str, Optional[float]] = {},
    less: Dict[str, Optional[float]] = {},
    less_equal: Dict[str, Optional[float]] = {},
    greater: Dict[str, Optional[float]] = {},
    greater_equal: Dict[str, Optional[float]] = {},
) -> str:
    cond = []

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
        filename: Filename of the database
        query: SQL Query

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
    col_value: str,
    col_index: str,
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
        col_value: Name of the relevant column, e.g. Time
        col_index: Name of the index column
        fun_compare: Lambda function of the condition, e.g. `lambda t: t > 10` (Time > 10)
    """

    def get_value(index):
        cur = connection.execute(
            f"SELECT {col_value} FROM {table} WHERE {col_index} == {index}"
        )
        return cur.fetchone()[0]

    i_min = connection.execute(
        f"SELECT MIN({col_index}) FROM {table}"
    ).fetchone()[0]
    i_max = connection.execute(
        f"SELECT MAX({col_index}) FROM {table}"
    ).fetchone()[0]

    while True:
        c_min = fun_compare(get_value(i_min))
        c_max = fun_compare(get_value(i_max))

        if c_min and c_max:
            return None  # condition true for both limits
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


def insert_query_from_dict(table: str, row_dict: Dict[str, Any]) -> str:
    row_dict = remove_none_values_from_dict(row_dict)
    columns = [*row_dict]  # unpacking faster than list(row_dict.keys())

    # generate query
    # e.g.: INSERT INTO ae_data (SetID, Time, Channel) VALUES (:SetID, :Time, :Channel)
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
    query = insert_query_from_dict(table, row_dict)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid


def update_query_from_dict(table: str, row_dict: Dict[str, Any], key_column: str):
    row_dict = remove_none_values_from_dict(row_dict)
    columns = [*row_dict]
    try:
        columns.remove(key_column)
    except:
        raise ValueError(f"Argument key_column '{key_column}' must be a key of row_dict")

    # generate query
    # e.g.: UPDATE ae_data SET Time = :Time, Channel = :Channel WHERE SetID == :SetID
    query = "UPDATE {table} SET {set} WHERE {condition}".format(
        table=table,
        set=", ".join([f"{col} = :{col}" for col in columns]),
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
    query = update_query_from_dict(table, row_dict, key_column)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid
