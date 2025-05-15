from contextlib import closing
from typing import Union

import mysql.connector

import config

def db_conneсtion():
    db_connection = mysql.connector.connect(
        user=config.MYSQL_USER, password=config.MYSQL_PASSWORD,
        host=config.MYSQL_HOST,
        database='calls'
        )
    return db_connection


def execute_sql(operation_type: str, query: str, params: Union[tuple, dict, None] = None):
    """
    Выполняет SQL-запрос и возвращает результат в зависимости от типа операции.

    :param operation_type: 'select_one', 'select_all', 'insert', 'update', 'delete'
    :param query: SQL-запрос с placeholder'ами (%s или %(name)s)
    :param params: параметры запроса (tuple, dict или None)

    :return: 
        - select_one -> Optional[tuple]
        - select_all -> List[tuple]
        - insert     -> int (lastrowid)
        - update/delete -> int (кол-во измененных строк)
    """
    with closing(db_conneсtion()) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(query, params or ())

                if operation_type == "select_one":
                    result = cur.fetchone()
                    return result  # Одна строка или None

                elif operation_type == "select_all":
                    result = cur.fetchall()
                    return result  # Список строк

                elif operation_type == "insert":
                    conn.commit()
                    return cur.lastrowid  # ID вставленной строки

                elif operation_type in ("update", "delete"):
                    rows_affected = cur.rowcount
                    conn.commit()
                    return rows_affected

                else:
                    raise ValueError(f"Неизвестный тип операции: {operation_type}")

            except Exception as e:
                conn.rollback()
                print(f"[SQL Ошибка] {e}")
                return None
