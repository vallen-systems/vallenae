import sqlite3
import pytest

from vallenae.io._sql import (
    query_conditions,
    count_sql_results,
    read_sql_generator,
    QueryIterable,
    insert_query_from_dict,
    insert_from_dict,
)


@pytest.fixture(name="memory_abc")
def fixture_memory_abc():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE abc (a INT, b INT, c INT)")
    # add 10 rows of dummy data
    for i in range(10):
        con.execute(
            "INSERT INTO abc (a, b, c) VALUES ({:d}, {:d}, {:d})".format(i, 10 + i, 20 + i)
        )

    yield con
    con.close()


@pytest.fixture(name="memory_id_abc")
def fixture_memory_id_abc():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE abc (id INT UNIQUE NOT NULL, a INT, b INT, c INT)")
    yield con
    con.close()


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


def test_query_iterable(memory_abc):
    # simple conversion function dict to tuple
    def dict_to_type_func(row_dict):
        return (row_dict["a"], row_dict["b"], row_dict["c"])

    iterable = QueryIterable(memory_abc, "SELECT * FROM abc", dict_to_type_func)

    assert len(iterable) == 10

    for index, row in enumerate(iterable):
        assert row == (index, 10 + index, 20 + index)


def test_insert_query_from_dict():
    row_dict = {"a": 1, "b": 2, "c": 3}
    assert insert_query_from_dict("abc", row_dict) == "INSERT INTO abc (a, b, c) VALUES (:a, :b, :c)"

    row_dict = {"a": 1, "b": None, "c": 3}
    assert insert_query_from_dict("abc", row_dict) == "INSERT INTO abc (a, c) VALUES (:a, :c)"


def test_insert_from_dict(memory_id_abc):
    def get_row_by_id(row_id: int):
        cur = memory_id_abc.execute("SELECT * FROM abc WHERE id == {:d}".format(row_id))
        columns = [column[0] for column in cur.description]
        values = cur.fetchone()
        return dict(zip(columns, values))

    insert_from_dict(memory_id_abc, "abc", {"id": 1, "a": 1})
    insert_from_dict(memory_id_abc, "abc", {"id": 2, "a": 2, "b": 1})
    insert_from_dict(memory_id_abc, "abc", {"id": 3, "a": 3, "b": 2, "c": 1})

    assert get_row_by_id(1) == {"id": 1, "a": 1, "b": None, "c": None}
    assert get_row_by_id(2) == {"id": 2, "a": 2, "b": 1, "c": None}
    assert get_row_by_id(3) == {"id": 3, "a": 3, "b": 2, "c": 1}
