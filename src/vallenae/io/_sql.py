import collections.abc
import contextlib
import logging
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Sequence, Tuple, TypeVar, Union

from .types import SizedIterable

logger = logging.getLogger(__name__)


def create_uri(filename: Union[str, Path], *, mode: str = "ro") -> str:
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
        dict_to_type: Callable[[Dict[str, Any]], T],
    ):
        super().__init__()
        self._connection_wrapper = connection_wrapper
        self._query = query
        self._dict_to_type = dict_to_type
        self._count_result: Optional[int] = None  # cache result of __len__

    def __len__(self) -> int:
        if self._count_result is None:
            self._count_result = count_sql_results(
                self._connection_wrapper.connection(),
                self._query
            )
        return self._count_result

    def __iter__(self) -> Iterator[T]:
        if self.__len__() == 0:
            logger.debug("Empty SQLite query")

        for row in read_sql_generator(self._connection_wrapper.connection(), self._query):
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
    custom_filter: Optional[str] = None,
) -> str:
    cond = []

    if isin is not None:
        for key, values in isin.items():
            if values is None:
                continue
            if not isinstance(values, collections.abc.Sequence):
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

    if custom_filter is not None:
        cond.append(f"({custom_filter})")  # wrap custom condition(s) in brackets

    return "WHERE " + " AND ".join(cond) if cond else ""


def read_sql_generator(
    connection: sqlite3.Connection, query: str, *parameter,
) -> Iterator[Dict[str, Any]]:
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
) -> Optional[int]:
    """
    Helper function to find the boundary index for given condition on a sorted column.

    Especially using conditions on the pridb's and tradb's Time column are expensive (not indexed).
    E.g.: SELECT * FROM view_tr_data WHERE Time > 10 AND Time < 100

    Because the Time column is monotonic increasing, a fast binary search can be applied.
    The Time column is not *stricly* monotonic increasing; different channels might share the same
    timestamp. To find the lower/upper bound of same values, a subsequent linear search is applied.

    Args:
        connection: SQLite connection
        table: Table name
        column_value: Name of the sorted column, e.g. Time
        column_index: Name of the indexed column
        fun_compare: Lambda function of the condition, e.g. `lambda t: t > 10` (Time > 10)
        lower_bound: Specify which index to return for ranges of same values.
            Default: Return lower bound (`True`)
    """

    # two querys are way faster than one combined!
    i_min_total = connection.execute(f"SELECT MIN({column_index}) FROM {table}").fetchone()[0]
    i_max_total = connection.execute(f"SELECT MAX({column_index}) FROM {table}").fetchone()[0]

    def get_value(index):
        cur = connection.execute(
            f"SELECT {column_value} FROM {table} WHERE {column_index} == ?", (index,)
        )
        return cur.fetchone()[0]

    def binary_search():
        i_min, i_max = i_min_total, i_max_total
        while True:
            v_min = get_value(i_min)
            v_max = get_value(i_max)
            if v_min > v_max:
                raise ValueError(f"Value column {column_value} not sorted")
            c_min = fun_compare(v_min)
            c_max = fun_compare(v_max)

            if c_min and c_max:  # condition true for both limits
                return i_min if lower_bound else i_max
            if not c_min and not c_max:  # condition false for both limits
                return None

            if i_max - i_min < 2:
                return i_min if c_min is True else i_max

            i_mid = (i_max + i_min) // 2
            c_mid = fun_compare(get_value(i_mid))

            if c_mid == c_min:
                i_min = i_mid
            else:
                i_max = i_mid

    def bound_same_value(start: int):
        """Find lower/upper bound of same values with linear search."""
        v_start = get_value(start)
        inc = -1 if lower_bound else 1
        i = start
        while i_min_total < i < i_max_total:
            i += inc
            if get_value(i) != v_start:
                return i - inc
        return i

    i = binary_search()
    if i is not None:
        return bound_same_value(i)
    return i


def create_new_database(filename: str, schema: str):
    if Path(filename).resolve().exists():
        raise ValueError("Can not create new database. File already exists")

    # open database in read-write-create mode
    with contextlib.closing(
        sqlite3.connect(create_uri(filename, mode="rwc"), uri=True)
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
        raise ValueError(f"Argument key_column '{key_column}' must be a key of row_dict") from None

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
