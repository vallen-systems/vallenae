from __future__ import annotations

import collections.abc
import contextlib
import logging
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence, TypeVar

from ._types import SizedIterable

logger = logging.getLogger(__name__)


def create_uri(filename: str | Path, *, mode: str = "ro") -> str:
    """Create SQLite URI (https://www.sqlite.org/uri.html)."""

    filepath = Path(filename)
    uri_path = filepath.as_posix()
    uri_path = uri_path.replace("?", "%3f")
    uri_path = uri_path.replace("#", "%23")
    return f"file:{uri_path}?mode={mode}"


class ConnectionWrapper:
    """SQLite3 connection wrapper (picklable)."""

    def __init__(self, filename: str, mode: str = "ro", multithreading: bool = False):
        # check mode
        valid_modes = ("ro", "rw", "rwc")
        if mode not in valid_modes:
            raise ValueError(f"Invalid access mode '{mode}', use: {valid_modes}")

        self._filename = str(filename)
        self._mode = mode
        self._multithreading = multithreading
        # enable multithreading for read-only connections
        if mode == "ro":
            self._multithreading = True

        self._connected = False
        self._connect()

    def _connect(self):
        """Open SQLite connection."""
        self._connection = sqlite3.connect(
            create_uri(self._filename, mode=self._mode),
            uri=True,
            check_same_thread=(not self._multithreading),
        )
        self._connected = True

        # set pragmas for write-mode
        if self._mode != "ro":
            self._connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA synchronous = OFF;
                """
            )

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def connected(self) -> bool:
        return self._connected

    def connection(self) -> sqlite3.Connection:
        """
        Get SQLite connection object.

        Raises:
            RuntimeError: If connection is closed
        """
        if not self._connected:
            raise RuntimeError("Not connected to SQLite database")
        return self._connection

    def get_readonly_connection(self) -> "ConnectionWrapper":
        """
        Return read-only ConnectionWrapper.

        Create new connection if mode != ro.
        """
        if self._mode == "ro":
            return self
        return ConnectionWrapper(self._filename, mode="ro")

    def close(self):
        if self._connected:
            self._connection.commit()  # commit remaining changes
            self._connection.close()
            self._connected = False

    def __del__(self):
        self.close()

    def __getstate__(self):
        # commit changes, database will be reopened with __setstate__
        if self._connected:
            self._connection.commit()
        state = self.__dict__.copy()
        del state["_connection"]  # remove the unpicklable sqlite3.connection
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # reopen connection if connected before
        if self._connected:
            self._connect()


T = TypeVar("T")


class QueryIterable(SizedIterable[T]):
    """
    Sized iterable to query results from SQLite as dictionaries.

    SQLite connection is stored in picklable ConnectionWrapper to be used with multiprocessing.
    """

    def __init__(
        self,
        connection_wrapper: ConnectionWrapper,
        query: str,
        dict_to_type: Callable[[dict[str, Any]], T],
    ):
        super().__init__()
        self._connection_wrapper = connection_wrapper
        self._query = query
        self._dict_to_type = dict_to_type
        self._count_result: int | None = None  # cache result of __len__

    def __len__(self) -> int:
        if self._count_result is None:
            self._count_result = count_sql_results(
                self._connection_wrapper.connection(), self._query
            )
        return self._count_result

    def __iter__(self) -> Iterator[T]:
        if self.__len__() == 0:
            logger.debug("Empty SQLite query")

        for row in read_sql_generator(self._connection_wrapper.connection(), self._query):
            yield self._dict_to_type(row)


def query_conditions(
    *,
    isin: dict[str, float | Sequence[float] | None] | None = None,
    equal: dict[str, float | None] | None = None,
    less: dict[str, float | None] | None = None,
    less_equal: dict[str, float | None] | None = None,
    greater: dict[str, float | None] | None = None,
    greater_equal: dict[str, float | None] | None = None,
    custom_filter: str | None = None,
) -> str:
    cond = []

    def as_sequence(value):
        return value if isinstance(value, collections.abc.Sequence) else (value,)

    if isin is not None:
        for key, values in isin.items():
            if values is None:
                continue
            list_values = ", ".join(str(value) for value in as_sequence(values))
            cond.append(f"{key} IN ({list_values})")

    comparison = {
        "==": equal,
        "<": less,
        "<=": less_equal,
        ">": greater,
        ">=": greater_equal,
    }

    def escape_string(value):
        return f"'{value}'" if isinstance(value, str) else value

    for comp_operator, comp_dict in comparison.items():
        if comp_dict is not None:
            for key, value in comp_dict.items():
                if value is None:
                    continue
                cond.append(f"{key} {comp_operator} {escape_string(value)}")

    if custom_filter is not None:
        cond.append(f"({custom_filter})")  # wrap custom condition(s) in brackets

    return "WHERE " + " AND ".join(cond) if cond else ""


def read_sql_generator(
    connection: sqlite3.Connection,
    query: str,
    *parameter,
) -> Iterator[dict[str, Any]]:
    """
    Generator to query data from a SQLite connection as a dictionary.

    Args:
        connection: SQLite3 connection object
        query: SELECT Query

    Yields:
        Row of the query result set as namedtuple
    """
    cur = connection.execute(query, parameter)
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
    *,
    lower_bound: bool = True,
) -> int | None:
    """
    Find a boundary index for a monotonic condition on a value column sorted by an index column.

    Conditions on the pridb's and tradb's Time column are expensive (Time is not indexed),
    e.g.: SELECT * FROM view_tr_data WHERE Time > 10 AND Time < 100

    Because Time increases monotonically with the indexed column (e.g. the tradb's TRAI), a fast
    binary search over the index column can locate the boundary instead. The index column is
    monotonic but *not* dense - it may contain gaps (missing values) - so each probe is snapped
    to the nearest existing row in the search direction; a missing index is never queried.

    Args:
        connection: SQLite connection
        table: Table name
        column_value: Name of the sorted (monotonic) column, e.g. Time
        column_index: Name of the indexed column, e.g. TRAI
        fun_compare: Lambda function of the condition, e.g. `lambda t: t > 10` (Time > 10).
            The condition must be monotonic in `column_value`, i.e. switch from `False` to `True`
            (use `lower_bound=True`) or from `True` to `False` (use `lower_bound=False`) exactly
            once over the sorted range.
        lower_bound: Search direction. `True` snaps probes upwards and returns the boundary at the
            lower end of the matching range (for `False`->`True` conditions). `False` snaps
            downwards and returns the boundary at the upper end (for `True`->`False` conditions).
            Default: `True`.

    Returns:
        The existing `column_index` value at the boundary of the matching rows, or `None` if the
        condition is `False` for every row.

        When several rows share the boundary value (e.g. simultaneous records on different
        channels sharing a timestamp), `lower_bound=True` returns the **first** of them and
        `lower_bound=False` the **last**, so the result is safe as an inclusive bound on
        `column_index` (`column_index >= result` / `column_index <= result`). The index column
        may be sparse (contain gaps); the search never queries a missing index and always
        returns an existing one.
    """

    # two querys are way faster than one combined!
    i_min = connection.execute(f"SELECT MIN({column_index}) FROM {table}").fetchone()[0]
    i_max = connection.execute(f"SELECT MAX({column_index}) FROM {table}").fetchone()[0]
    if i_min is None:  # empty table
        return None

    def value_at(index):
        return connection.execute(
            f"SELECT {column_value} FROM {table} WHERE {column_index} == ?", (index,)
        ).fetchone()[0]

    def neighbour(index, op, order):
        """Nearest existing row in a direction, snapping over index gaps."""
        return connection.execute(
            f"SELECT {column_index}, {column_value} FROM {table} "
            f"WHERE {column_index} {op} ? ORDER BY {column_index} {order} LIMIT 1",
            (index,),
        ).fetchone()

    # i_low/i_high are existing indices; condition differs between them once narrowed
    i_low, i_high = i_min, i_max
    v_low, v_high = value_at(i_low), value_at(i_high)
    if v_low > v_high:
        raise ValueError(f"Value column {column_value} not sorted")
    c_low, c_high = fun_compare(v_low), fun_compare(v_high)
    if c_low == c_high:  # condition constant over the whole range
        if not c_low:
            return None  # never matches
        return i_min if lower_bound else i_max  # always matches

    # Binary search for two adjacent *existing* rows that straddle the transition. Each probe is
    # snapped to an existing index near the midpoint, so a gap in the index column is never queried.
    while True:
        i_mid = (i_low + i_high) // 2
        row = neighbour(i_mid, "<=", "DESC")  # existing index in (i_low, i_mid]
        if row is None or row[0] <= i_low:
            row = neighbour(i_mid, ">", "ASC")  # else the next existing index above i_mid
        if row is None or row[0] >= i_high:
            break  # i_low and i_high are adjacent existing rows
        if fun_compare(row[1]) == c_low:
            i_low = row[0]
        else:
            i_high = row[0]

    # Walk to the requested edge of the run of rows sharing the boundary (True-side) value.
    boundary = i_low if c_low else i_high
    value = value_at(boundary)
    op, order = ("<", "DESC") if lower_bound else (">", "ASC")
    while True:
        row = neighbour(boundary, op, order)
        if row is None or row[1] != value:
            return boundary
        boundary = row[0]


def create_new_database(filename: str, schema: str):
    if Path(filename).resolve().exists():
        raise ValueError("Can not create new database. File already exists")

    # open database in read-write-create mode
    with contextlib.closing(sqlite3.connect(create_uri(filename, mode="rwc"), uri=True)) as con:
        con.executescript(schema)


def remove_none_values_from_dict(dictionary: dict[Any, Any]):
    """Helper function to remove None values from dict."""
    return {k: v for k, v in dictionary.items() if v is not None}


@lru_cache(maxsize=128, typed=True)
def generate_insert_query(table: str, columns: tuple[str, ...]) -> str:
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
    query_columns = ", ".join(columns)
    query_placeholder = ", ".join(f":{col}" for col in columns)
    return f"INSERT INTO {table} ({query_columns}) VALUES ({query_placeholder})"


def insert_from_dict(
    connection: sqlite3.Connection,
    table: str,
    row_dict: dict[str, Any],
) -> int:
    """INSERT row for given dict of column names -> values in SQLite table."""
    row_dict = remove_none_values_from_dict(row_dict)
    columns = tuple(row_dict.keys())
    query = generate_insert_query(table, columns)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid or 0


@lru_cache(maxsize=128, typed=True)
def generate_update_query(table: str, columns: tuple[str, ...], key_column: str) -> str:
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
        raise ValueError(f"Argument key_column '{key_column}' must be a key of row_dict") from None

    query_set = ", ".join([f"{col} = :{col}" for col in columns_list])
    query_where = f"{key_column} == :{key_column}"
    return f"UPDATE {table} SET {query_set} WHERE {query_where}"


def update_from_dict(
    connection: sqlite3.Connection,
    table: str,
    row_dict: dict[str, Any],
    key_column: str,
) -> int:
    """UPDATE row for given key and dict of column names -> values in SQLite table."""
    row_dict = remove_none_values_from_dict(row_dict)
    columns = tuple(row_dict.keys())
    query = generate_update_query(table, columns, key_column)
    cur = connection.execute(query, row_dict)
    return cur.lastrowid or 0
