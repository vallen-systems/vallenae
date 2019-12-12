from pathlib import Path
import sqlite3
from functools import wraps
from typing import Optional, Set, Tuple, Dict, Any
from ast import literal_eval

from ._sql import read_sql_generator


def require_write_access(func):
    @wraps(func)
    def wrapper(self: "Database", *args, **kwargs):
        if self.readonly:
            raise ValueError(
                "Can not write to database in read-only mode. Open database with readonly=False"
            )
        return func(self, *args, **kwargs)
    return wrapper


class Database:
    """Database base class for pridb, tradb and trfdb."""

    def __init__(
        self,
        filename: str,
        *,
        table_prefix: str,
        readonly: bool = True,
        required_file_ext: Optional[str] = None,
    ):
        # forced str conversion (e.g. for pathlib.Path)
        self._filename: str = str(filename)
        self._readonly: bool = readonly

        if required_file_ext is not None:
            file_ext = Path(self._filename).suffix[1:]
            if file_ext.lower() != required_file_ext.lower():
                raise ValueError(
                    "File extension '{:s}' must match '{:s}'".format(
                        file_ext, required_file_ext,
                    )
                )

        self._connected: bool = False
        self._connection = sqlite3.connect(
            "file:{:s}?mode={:s}".format(self._filename, "ro" if readonly else "rw"),
            uri=True,
        )
        self._connected = True

        # set pragmas for write-mode
        if not self._readonly:
            self._connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA locking_mode = EXCLUSIVE;
                PRAGMA synchronous = OFF;
                """
            )

        self._table_prefix: str = table_prefix
        self._table_main: str = "{:s}_data".format(table_prefix)
        self._table_globalinfo: str = "{:s}_globalinfo".format(table_prefix)
        self._table_params: str = "{:s}_params".format(table_prefix)

        # check if main table (<prefix>_data) exists
        if self._table_main not in self.tables():
            raise ValueError(
                "Main table '{:s}' does not exist in database".format(self._table_main)
            )

    @property
    def filename(self) -> str:
        """Filename of database."""
        return self._filename

    @property
    def readonly(self) -> bool:
        """Read-only mode for database connection."""
        return self._readonly

    @property
    def connected(self) -> bool:
        """Check if connected to SQLite database."""
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

    def rows(self) -> int:
        """Number of rows in data table."""
        con = self.connection()
        cur = con.execute("SELECT COUNT(*) FROM {:s}".format(self._table_main))
        return cur.fetchone()[0]

    def columns(self) -> Tuple[str, ...]:
        """Columns of data table."""
        con = self.connection()
        # empty dummy query
        cur = con.execute("SELECT * FROM {:s} LIMIT 0".format(self._table_main))
        return tuple(str(column[0]) for column in cur.description)

    def tables(self) -> Set[str]:
        """Get table names."""
        con = self.connection()
        cur = con.execute("SELECT name FROM sqlite_master WHERE type == 'table'")
        tables = {result[0] for result in cur.fetchall()}
        return tables

    def globalinfo(self) -> Dict[str, Any]:
        """Content from globalinfo table."""
        def try_convert_string(value: str) -> Any:
            try:
                return literal_eval(value)
            except SyntaxError:
                return str(value)
        con = self.connection()
        cur = con.execute("SELECT Key, Value FROM {:s}".format(self._table_globalinfo))
        return {
            row[0]: try_convert_string(str(row[1])) for row in cur.fetchall()
        }

    @require_write_access
    def _update_globalinfo(self):
        """Update globalinfo after writes."""
        keys = self.globalinfo().keys()
        if "ValidSets" in keys:
            self.connection().execute(
                """
                UPDATE {prefix}_globalinfo
                SET Value = (SELECT MAX(SetID) FROM {prefix}_data)
                WHERE Key == "ValidSets"
                """.format(prefix=self._table_prefix)
            )
        if "TRAI" in keys:
            self.connection().execute(
                """
                UPDATE {prefix}_globalinfo
                SET Value = (SELECT MAX(TRAI) FROM {prefix}_data)
                WHERE Key == "TRAI";
                """.format(prefix=self._table_prefix)
            )

    def _parameter_table(self) -> Dict[int, Dict[str, Any]]:
        """Read *_params table to dict."""
        def parameter_by_id():
            for row in read_sql_generator(
                self.connection(),
                "SELECT * FROM {:s}".format(self._table_params),
            ):
                param_id = row.pop("ID")
                yield (param_id, row)
        return dict(parameter_by_id())

    def _parameter(self, param_id: int) -> Dict[str, Any]:
        """Read parameters from *_params by ID."""
        try:
            return self._parameter_table()[param_id]
        except KeyError:
            raise ValueError(
                "Parameter ID {:d} not found in {:s}".format(
                    param_id, self._table_params
                )
            )

    def close(self):
        """Close database connection."""
        if self._connected:
            if not self._readonly:
                self._update_globalinfo()
                self._connection.commit()  # commit remaining changes
            self._connection.close()
            self._connected = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
