import sqlite3
from math import sin
import pytest

from vallenae.io._sql import (
    query_conditions,
    count_sql_results,
    read_sql_generator,
    QueryIterable,
    sql_binary_search,
    generate_insert_query,
    insert_from_dict,
    generate_update_query,
    update_from_dict,
)


@pytest.fixture(name="memory_abc")
def fixture_memory_abc():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE abc (a INT, b INT, c INT)")
    # add 10 rows of dummy data
    for i in range(10):
        con.execute(
            f"INSERT INTO abc (a, b, c) VALUES ({i}, {10 + i}, {20 + i})"
        )
    yield con
    con.close()


@pytest.fixture(name="memory_id_abc")
def fixture_memory_id_abc():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE abc (id INT UNIQUE NOT NULL, a INT, b INT, c INT)")
    yield con
    con.close()


def get_row_by_id(connection, table, row_id):
    cur = connection.execute(f"SELECT * FROM {table} WHERE id == {row_id}")
    columns = [column[0] for column in cur.description]
    values = cur.fetchone()
    if values is None:
        return None
    return dict(zip(columns, values))


def test_sql_query_conditions():
    # no or none values
    assert query_conditions() == ""
    assert query_conditions(isin={"Number": None}) == ""
    assert query_conditions(equal={"Number": None}) == ""
    assert query_conditions(less={"Number": None}) == ""
    assert query_conditions(less_equal={"Number": None}) == ""
    assert query_conditions(greater={"Number": None}) == ""
    assert query_conditions(greater_equal={"Number": None}) == ""

    # single conditions
    assert query_conditions(
        isin={"Number": (1, 2, 3)}
    ) == "WHERE Number IN (1, 2, 3)"

    assert query_conditions(
        isin={"Number": 1.1}
    ) == "WHERE Number IN (1.1)"

    assert query_conditions(
        equal={"Str": "value"}
    ) == "WHERE Str == 'value'"

    assert query_conditions(
        less={"a": 1.1}
    ) == "WHERE a < 1.1"

    assert query_conditions(
        less_equal={"a": 2.2}
    ) == "WHERE a <= 2.2"

    assert query_conditions(
        greater={"a": 3.3}
    ) == "WHERE a > 3.3"

    assert query_conditions(
        greater_equal={"a": 4.4}
    ) == "WHERE a >= 4.4"

    # multiple conditions
    assert query_conditions(
        equal={"a": 0},
        less={"b": 1},
        less_equal={"c": 2},
        greater={"d": 3},
        greater_equal={"e": 4}
    ) == "WHERE a == 0 AND b < 1 AND c <= 2 AND d > 3 AND e >= 4"


def test_count_sql_results(memory_abc):
    query_all = "SELECT * FROM abc"

    assert count_sql_results(memory_abc, query_all) == 10
    assert count_sql_results(memory_abc, query_all + " WHERE a >= 0") == 10
    assert count_sql_results(memory_abc, query_all + " WHERE b >= 0") == 10
    assert count_sql_results(memory_abc, query_all + " WHERE c >= 0") == 10

    assert count_sql_results(memory_abc, query_all + " WHERE a >= 3") == 7
    assert count_sql_results(memory_abc, query_all + " WHERE a == 1") == 1

    assert count_sql_results(memory_abc, query_all + " WHERE b >= 15") == 5
    assert count_sql_results(memory_abc, query_all + " WHERE b == 11") == 1
    assert count_sql_results(memory_abc, query_all + " WHERE b == 9") == 0

    assert count_sql_results(memory_abc, query_all + " WHERE c >= 22") == 8
    assert count_sql_results(memory_abc, query_all + " WHERE c == 22") == 1
    assert count_sql_results(memory_abc, query_all + " WHERE c == 111") == 0


def test_read_sql_generator(memory_abc):
    for index, row_dict in enumerate(read_sql_generator(memory_abc, "SELECT * FROM abc")):
        assert len(row_dict) == 3
        assert list(row_dict.keys()) == ["a", "b", "c"]
        assert row_dict["a"] == index
        assert row_dict["b"] == 10 + index
        assert row_dict["c"] == 20 + index


def test_sql_binary_search():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE squares (id INTEGER PRIMARY KEY, value REAL)")
    con.execute("CREATE TABLE consts (id INTEGER PRIMARY KEY, value INT)")
    con.execute("CREATE TABLE sin (id INTEGER PRIMARY KEY, value REAL)")
    for i in range(100):
        con.execute("INSERT INTO squares (id, value) VALUES (?, ?)", (i, i**2))
        con.execute("INSERT INTO consts (id, value) VALUES (?, ?)", (i, 11))
        con.execute("INSERT INTO sin (id, value) VALUES (?, ?)", (i, sin(i)))

    # squares table
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x < 0) == None
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x > 99**2) == None

    assert sql_binary_search(con, "squares", "value", "id", lambda x: x > 9) == 4
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x >= 9) == 3
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x < 9) == 2

    assert sql_binary_search(con, "squares", "value", "id", lambda x: x > 256) == 17
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x >= 256) == 16
    assert sql_binary_search(con, "squares", "value", "id", lambda x: x < 256) == 15

    # consts table
    assert sql_binary_search(con, "consts", "value", "id", lambda x: x < 11) == None
    assert sql_binary_search(con, "consts", "value", "id", lambda x: x > 11) == None

    # condition true for all values, expect first matching index (0)
    assert sql_binary_search(con, "consts", "value", "id", lambda x: x >= 11) == 0
    assert sql_binary_search(con, "consts", "value", "id", lambda x: x == 11) == 0
    assert sql_binary_search(con, "consts", "value", "id", lambda x: x <= 11) == 0

    # sin table, not sorted -> expect exception
    with pytest.raises(ValueError):
        for limit in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            sql_binary_search(con, "sin", "value", "id", lambda x: x >= limit)

    con.close()


def test_query_iterable(memory_abc):
    # simple conversion function dict to tuple
    def dict_to_type_func(row_dict):
        return (row_dict["a"], row_dict["b"], row_dict["c"])

    iterable = QueryIterable(memory_abc, "SELECT * FROM abc", dict_to_type_func)

    assert len(iterable) == 10

    for index, row in enumerate(iterable):
        assert row == (index, 10 + index, 20 + index)


def test_generate_insert_query():
    assert generate_insert_query("abc", ("a")) == "INSERT INTO abc (a) VALUES (:a)"
    assert generate_insert_query("abc", ("a", "b", "c")) == "INSERT INTO abc (a, b, c) VALUES (:a, :b, :c)"


def test_insert_from_dict(memory_id_abc):
    row_by_id = lambda row_id: get_row_by_id(memory_id_abc, "abc", row_id)

    assert insert_from_dict(memory_id_abc, "abc", {"id": 1, "a": 1}) == 1
    assert insert_from_dict(memory_id_abc, "abc", {"id": 2, "a": 2, "b": 1}) == 2
    assert insert_from_dict(memory_id_abc, "abc", {"id": 3, "a": 3, "b": 2, "c": 1}) == 3

    assert row_by_id(1) == {"id": 1, "a": 1, "b": None, "c": None}
    assert row_by_id(2) == {"id": 2, "a": 2, "b": 1, "c": None}
    assert row_by_id(3) == {"id": 3, "a": 3, "b": 2, "c": 1}

    with pytest.raises(sqlite3.OperationalError):
        insert_from_dict(memory_id_abc, "abc", {"not_existing_column": 111})


def test_generate_update_query():
    assert generate_update_query("abc", ("a", "b"), "a") == "UPDATE abc SET b = :b WHERE a == :a"
    assert generate_update_query("abc", ("a", "b", "c"), "a") == "UPDATE abc SET b = :b, c = :c WHERE a == :a"

    with pytest.raises(ValueError):
        generate_update_query("abc", ("a"), "xyz")  # xyz not a column


def test_update_from_dict(memory_id_abc):
    row_by_id = lambda row_id: get_row_by_id(memory_id_abc, "abc", row_id)

    memory_id_abc.execute("INSERT INTO abc (id, a, b, c) VALUES (1, 11, 22, 33)")
    assert row_by_id(1) == {"id": 1, "a": 11, "b": 22, "c": 33}

    assert update_from_dict(memory_id_abc, "abc", {"id": 1, "a": 0, "b": 0, "c": 0}, "id") == 1
    assert row_by_id(1) == {"id": 1, "a": 0, "b": 0, "c": 0}

    assert update_from_dict(memory_id_abc, "abc", {"id": 1, "a": 100}, "id") == 1
    assert row_by_id(1) == {"id": 1, "a": 100, "b": 0, "c": 0}

    with pytest.raises(ValueError):
        update_from_dict(memory_id_abc, "abc", {"a": 100}, "id")  # id not in dict

    with pytest.raises(sqlite3.OperationalError):
        update_from_dict(memory_id_abc, "abc", {"id": 1, "not_existing_column": 111}, "id")
