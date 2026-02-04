# -*- coding: utf-8 -*-
"""DB 연결, 쿼리 실행, 결과 반환

sqlite3 표준 라이브러리만 사용하며, 쿼리 결과를 딕셔너리 리스트로 반환한다.
"""

import os
import sqlite3
import sys

from core.config import DB_PATH


def get_connection(db_path=None):
    """SQLite DB 연결을 반환한다."""
    path = db_path or DB_PATH
    if not os.path.exists(path):
        print(f'오류: DB 파일을 찾을 수 없습니다: {path}', file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(sql, params=None, db_path=None):
    """쿼리를 실행하고 결과를 딕셔너리 리스트로 반환한다."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, [dict(row) for row in rows]
    finally:
        conn.close()


def execute_scalar(sql, params=None, db_path=None):
    """단일 값을 반환하는 쿼리를 실행한다."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_latest_date(db_path=None):
    """promotion_list에서 가장 최근 승진년월을 반환한다."""
    return execute_scalar(
        "SELECT MAX(승진년월) FROM promotion_list",
        db_path=db_path
    )


def get_all_dates(db_path=None):
    """전체 승진년월 목록을 반환한다 (내림차순)."""
    _, rows = execute_query(
        "SELECT 승진년월, COUNT(*) AS 승진자수 FROM promotion_list GROUP BY 승진년월 ORDER BY 승진년월 DESC",
        db_path=db_path
    )
    return rows


def validate_date(date_str, db_path=None):
    """승진년월 형식(YYYYMM)을 검증하고 존재 여부를 확인한다."""
    if not date_str:
        return None, '승진년월이 지정되지 않았습니다.'
    try:
        date_int = int(date_str)
    except ValueError:
        return None, f'올바른 형식이 아닙니다: {date_str} (YYYYMM 형식 필요)'

    year = date_int // 100
    month = date_int % 100
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        return None, f'유효하지 않은 날짜입니다: {date_str}'

    count = execute_scalar(
        "SELECT COUNT(*) FROM promotion_list WHERE 승진년월 = ?",
        (date_int,),
        db_path=db_path
    )
    if count == 0:
        return None, f'해당 승진년월의 데이터가 없습니다: {date_str}'

    return date_int, None


def validate_filter(scope, filter_value, db_path=None):
    """범위 필터의 유효성을 검증한다."""
    if scope == '전행' or not filter_value:
        return True, None

    scope_table_map = {
        '그룹': ('HR', '그룹'),
        '부점': ('HR', '부점'),
        '세분': ('HR', '세분'),
    }

    if scope in scope_table_map:
        table, col = scope_table_map[scope]
        count = execute_scalar(
            f"SELECT COUNT(*) FROM {table} WHERE {col} = ? AND 인원포함여부 = 1",
            (filter_value,),
            db_path=db_path
        )
        if count == 0:
            return False, f'해당 {scope}을(를) 찾을 수 없습니다: {filter_value}'

    return True, None
