# -*- coding: utf-8 -*-
"""
PDFtable2db - PDF 표 추출 및 SQLite DB 저장 스크립트
Version: 1.1.0

PDF 파일에서 표(table)를 추출하여 SQLite 데이터베이스로 저장합니다.
한글 인코딩(UTF-8)을 완벽하게 지원합니다.
금융 보고서의 2열 레이아웃을 지원합니다.

Usage:
    # 추출 모드
    python pdftable2db.py <input.pdf> <output.db> [options]

    # 조회 모드
    python pdftable2db.py <db_path> --info
    python pdftable2db.py <db_path> --list-tables
    python pdftable2db.py <db_path> --show-table <id>

    # 내보내기 모드
    python pdftable2db.py <db_path> --export-csv <dir>
    python pdftable2db.py <db_path> --export-md <file>
"""

import sys
import os
import argparse
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 한글 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import pdfplumber
except ImportError:
    print("오류: pdfplumber가 설치되어 있지 않습니다.")
    print("설치: pip install pdfplumber")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    pd = None
    print("경고: pandas가 설치되어 있지 않습니다. 일부 기능이 제한됩니다.")


# =============================================================================
# DB 스키마 정의
# =============================================================================

SCHEMA_BASIC = """
-- PDF 소스 정보
CREATE TABLE IF NOT EXISTS pdf_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT,
    title TEXT,
    total_pages INTEGER,
    processed_pages TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 추출된 표 정보
CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_id INTEGER REFERENCES pdf_sources(id),
    page_num INTEGER NOT NULL,
    table_index INTEGER NOT NULL,
    rows INTEGER,
    cols INTEGER,
    category TEXT,
    company TEXT,
    bbox TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 표 데이터 (셀 단위)
CREATE TABLE IF NOT EXISTS table_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER REFERENCES tables(id),
    row_idx INTEGER NOT NULL,
    col_idx INTEGER NOT NULL,
    value TEXT,
    is_header INTEGER DEFAULT 0
);

-- 표 헤더 정보
CREATE TABLE IF NOT EXISTS table_headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER REFERENCES tables(id),
    col_idx INTEGER NOT NULL,
    header_name TEXT
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_tables_pdf ON tables(pdf_id);
CREATE INDEX IF NOT EXISTS idx_tables_page ON tables(page_num);
CREATE INDEX IF NOT EXISTS idx_data_table ON table_data(table_id);
CREATE INDEX IF NOT EXISTS idx_data_row ON table_data(row_idx);
"""

SCHEMA_FINANCIAL = """
-- 회사 마스터
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_eng TEXT
);

-- 지표 마스터
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    name_kor TEXT NOT NULL,
    name_eng TEXT,
    unit TEXT,
    UNIQUE(category, name_kor)
);

-- 시계열 재무 데이터
CREATE TABLE IF NOT EXISTS financial_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    metric_id INTEGER REFERENCES metrics(id),
    year INTEGER NOT NULL,
    is_estimate INTEGER DEFAULT 0,
    value REAL,
    source_table_id INTEGER REFERENCES tables(id),
    UNIQUE(company_id, metric_id, year)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_fin_company ON financial_data(company_id);
CREATE INDEX IF NOT EXISTS idx_fin_metric ON financial_data(metric_id);
CREATE INDEX IF NOT EXISTS idx_fin_year ON financial_data(year);
"""


# =============================================================================
# 단위 규칙 정의 (금융 보고서용)
# =============================================================================

UNIT_RULES = {
    # 십억원 (재무상태표/손익계산서 금액 항목)
    '십억원': [
        '현금및현금등가물', '현금 및 예치금', '유가증권', '투자금융자산',
        '대출채권', '이자부자산', '고정자산', '기타자산', '자산총계', '자산 총계',
        '예수금', '예수부채', '차입금', '차입부채/사채', '사채', '이자부부채',
        '기타부채', '부채총계', '부채 총계',
        '자본금', '신종자본증권', '자본잉여금', '이익잉여금', '자본조정',
        '기타포괄손익누계액', '소수주주지분', '자본총계', '자본 총계',
        '이자수익', '이자비용', '순이자이익', '순이자수익',
        '대손충당금', '충당금적립후순이자수익',
        '순수수료이익', '순수수료수익', '기타비이자이익합계', '총이익',
        '판매비와관리비', '판매관리비', '영업이익', '기타영업외이익',
        '법인세차감전순이익', '법인세비용차감전순이익', '법인세',
        '당기순이익', '당기순이익(연결)', '충당금적립전영업이익',
        '기타'
    ],
    # 원 (주당 금액)
    '원': [
        'EPS', '주당장부가', '주당 배당금 – 보통주', '주당배당금'
    ],
    # % (비율)
    '%': [
        'ROAA', 'ROAE', '순이자마진', '예대금리차*', '순이자마진*', 'NIM',
        '대출금성장률 (원화기준)', '예수금성장률 (원화기준)', '자산성장률',
        '대출금/예수금 (원화기준)', '비용/이익',
        'BIS 자기자본비율', 'Tier 1 자본비율', 'Tier 2 자본비율',
        '보통주 자본비율', '단순자기자본비율',
        '고정이하여신/총여신', '요주의이하여신/총여신',
        '대손충당금/고정이하여신', '대손충당금/요주의이하여신', '대손충당금/총여신',
        '순상각/고정이하여신', '순상각/총여신', '대손충당금 적립액/총여신',
        '배당성향 (%)', '주주환원율 (%)', '주주환원 성향 (%)', '배당성향', '주주환원율'
    ]
}


def get_metric_unit(metric_name: str) -> str:
    """지표명에 따른 단위 반환

    Args:
        metric_name: 지표명

    Returns:
        단위 문자열 (십억원, 원, %) 또는 None
    """
    if not metric_name:
        return None

    for unit, metrics in UNIT_RULES.items():
        if metric_name in metrics:
            return unit

    # 패턴 기반 추가 매칭
    name_lower = metric_name.lower()

    # % 패턴
    if any(kw in name_lower for kw in ['비율', '성장률', 'ratio', 'margin', 'roe', 'roa']):
        return '%'

    # EPS 패턴
    if '주당' in metric_name or 'eps' in name_lower:
        return '원'

    return None


# =============================================================================
# 유틸리티 함수
# =============================================================================

def parse_pages(pages_str: str, total_pages: int) -> list:
    """페이지 범위 문자열을 리스트로 변환"""
    if not pages_str:
        return list(range(total_pages))

    pages = []
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            start = int(start) - 1
            end = int(end)
            pages.extend(range(start, min(end, total_pages)))
        else:
            page = int(part) - 1
            if 0 <= page < total_pages:
                pages.append(page)

    return sorted(set(pages))


def clean_cell_value(value) -> str:
    """셀 값 정리"""
    if value is None:
        return ""
    text = str(value)
    text = ' '.join(text.split())
    text = text.replace('\n', ' ').replace('\r', '')
    return text.strip()


def parse_numeric_value(value_str: str) -> tuple:
    """숫자 값 파싱 (괄호는 음수)"""
    if not value_str:
        return None, False

    text = str(value_str).strip()
    is_estimate = 'E' in text.upper() and any(c.isdigit() for c in text)

    # 괄호 처리 (음수)
    negative = '(' in text and ')' in text

    # 숫자만 추출
    cleaned = ''.join(c for c in text if c.isdigit() or c in '.-')

    try:
        value = float(cleaned) if cleaned else None
        if negative and value:
            value = -abs(value)
        return value, is_estimate
    except ValueError:
        return None, is_estimate


# =============================================================================
# 좌표 기반 PDF 표 추출
# =============================================================================

def extract_tables_coordinate_based(pdf_path: str, pages: list = None, min_rows: int = 2) -> list:
    """좌표 기반 표 추출 (금융 보고서 2열 레이아웃 지원)

    Args:
        pdf_path: PDF 파일 경로
        pages: 처리할 페이지 리스트 (0-indexed)
        min_rows: 최소 행 수

    Returns:
        추출된 표 정보 리스트
    """
    results = []

    # 회사명 패턴
    company_patterns = [
        'KB금융', '신한지주', '하나금융지주', '우리금융지주',
        '기업은행', 'BNK금융지주', 'iM금융지주', 'JB금융지주', '카카오뱅크'
    ]

    # 표 카테고리 키워드
    category_keywords = {
        '재무상태표': ['재무상태표', '자산총계', '현금및현금등가물', '부채총계'],
        '손익계산서': ['손익계산서', '이자수익', '순이자이익', '영업이익'],
        '자산건전성': ['자산건전성', '고정이하여신', 'NPL'],
        '재무비율': ['재무비율', 'ROAA', 'ROAE', 'NIM'],
        '주당data': ['주당 data', 'EPS', '주당장부가'],
        '요약': ['충전영업이익', '순이익', 'P/E', 'P/B', '배당수익률']
    }

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        if pages is None:
            pages = list(range(total_pages))

        for page_idx in pages:
            if page_idx >= total_pages:
                continue

            page = pdf.pages[page_idx]
            page_width = page.width

            # 단어 추출 (좌표 포함)
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=True
            )

            if not words:
                continue

            # 회사명 감지
            page_text = ' '.join(w['text'] for w in words)
            company = None
            for pattern in company_patterns:
                if pattern in page_text:
                    company = pattern
                    break

            # Y좌표로 그룹화 (같은 줄)
            lines = defaultdict(list)
            for word in words:
                y = round(word['top'] / 5) * 5  # 5px 단위로 그룹화
                lines[y].append({
                    'x': word['x0'],
                    'text': word['text'],
                    'x1': word['x1']
                })

            # X좌표 중앙값으로 좌/우 열 분리 (2열 레이아웃)
            mid_x = page_width / 2

            # 표 데이터 추출
            left_table = {'category': '재무상태표', 'data': [], 'headers': []}
            right_table = {'category': '손익계산서', 'data': [], 'headers': []}

            year_pattern = re.compile(r'20\d\d[E]?')

            for y in sorted(lines.keys()):
                line_words = sorted(lines[y], key=lambda w: w['x'])

                # 좌/우 분리
                left_words = [w for w in line_words if w['x'] < mid_x - 20]
                right_words = [w for w in line_words if w['x'] >= mid_x - 20]

                # 좌측 처리
                if left_words:
                    left_text = ' '.join(w['text'] for w in left_words)

                    # 카테고리 감지
                    for cat, keywords in category_keywords.items():
                        if any(kw in left_text for kw in keywords):
                            if left_table['data']:  # 이전 데이터가 있으면 저장 X
                                pass
                            left_table['category'] = cat
                            break

                    # 연도 헤더 감지
                    if year_pattern.search(left_text) and '기준' in left_text:
                        years = year_pattern.findall(left_text)
                        left_table['headers'] = years
                    # 데이터 행 파싱
                    elif len(left_words) >= 2:
                        row = parse_data_row(left_words)
                        if row and len(row) >= 2:
                            left_table['data'].append(row)

                # 우측 처리
                if right_words:
                    right_text = ' '.join(w['text'] for w in right_words)

                    # 카테고리 감지
                    for cat, keywords in category_keywords.items():
                        if any(kw in right_text for kw in keywords):
                            right_table['category'] = cat
                            break

                    # 연도 헤더 감지
                    if year_pattern.search(right_text) and '기준' in right_text:
                        years = year_pattern.findall(right_text)
                        right_table['headers'] = years
                    # 데이터 행 파싱
                    elif len(right_words) >= 2:
                        row = parse_data_row(right_words)
                        if row and len(row) >= 2:
                            right_table['data'].append(row)

            # 결과 저장
            table_index = 0

            for table in [left_table, right_table]:
                if len(table['data']) >= min_rows:
                    # 헤더 행 추가
                    if table['headers']:
                        header_row = ['항목'] + table['headers']
                        table['data'].insert(0, header_row)

                    results.append({
                        'page_num': page_idx + 1,
                        'table_index': table_index,
                        'rows': len(table['data']),
                        'cols': max(len(row) for row in table['data']) if table['data'] else 0,
                        'category': table['category'],
                        'company': company,
                        'data': table['data'],
                        'page_text': page_text[:500]
                    })
                    table_index += 1

    return results


def parse_data_row(words: list) -> list:
    """단어 리스트에서 데이터 행 파싱

    Args:
        words: 단어 리스트 (x좌표 정렬됨)

    Returns:
        파싱된 행 데이터
    """
    if not words:
        return []

    # 첫 번째 요소: 항목명 (숫자가 아닌 것)
    # 나머지: 숫자 값들

    row = []
    current_text = ""

    for i, word in enumerate(words):
        text = word['text'].strip()
        if not text:
            continue

        # 숫자 여부 확인
        is_number = bool(re.match(r'^[\d,\.\(\)\-]+[E]?$', text.replace(' ', '')))

        if i == 0 or not is_number:
            # 항목명 부분
            if current_text:
                current_text += ' ' + text
            else:
                current_text = text
        else:
            # 숫자 값
            if current_text:
                row.append(current_text)
                current_text = ""
            row.append(text)

    if current_text:
        row.append(current_text)

    return row


def extract_tables_from_pdf(pdf_path: str, pages: list = None, min_rows: int = 2) -> list:
    """PDF에서 표 추출 (메인 함수)"""
    # 좌표 기반 추출 시도
    results = extract_tables_coordinate_based(pdf_path, pages, min_rows)

    if results:
        return results

    # 기본 pdfplumber 추출 시도
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        if pages is None:
            pages = list(range(total_pages))

        for page_idx in pages:
            if page_idx >= total_pages:
                continue

            page = pdf.pages[page_idx]
            page_text = page.extract_text() or ""

            tables = page.extract_tables()

            for table_idx, table in enumerate(tables):
                if not table or len(table) < min_rows:
                    continue

                cleaned_table = []
                for row in table:
                    cleaned_row = [clean_cell_value(cell) for cell in row]
                    if any(cleaned_row):
                        cleaned_table.append(cleaned_row)

                if len(cleaned_table) < min_rows:
                    continue

                results.append({
                    'page_num': page_idx + 1,
                    'table_index': table_idx,
                    'rows': len(cleaned_table),
                    'cols': max(len(row) for row in cleaned_table) if cleaned_table else 0,
                    'category': '기타',
                    'company': None,
                    'data': cleaned_table,
                    'page_text': page_text[:500]
                })

    return results


# =============================================================================
# DB 저장
# =============================================================================

def create_database(db_path: str, financial_mode: bool = False) -> sqlite3.Connection:
    """데이터베이스 생성"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA encoding = 'UTF-8'")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(SCHEMA_BASIC)

    if financial_mode:
        conn.executescript(SCHEMA_FINANCIAL)

    conn.commit()
    return conn


def save_to_database(conn: sqlite3.Connection, pdf_path: str,
                     tables: list, financial_mode: bool = False):
    """추출된 표를 DB에 저장"""
    cursor = conn.cursor()

    filename = os.path.basename(pdf_path)
    pages_processed = ','.join(str(t['page_num']) for t in tables)

    cursor.execute("""
        INSERT INTO pdf_sources (filename, filepath, total_pages, processed_pages)
        VALUES (?, ?, ?, ?)
    """, (filename, pdf_path, max(t['page_num'] for t in tables) if tables else 0, pages_processed))

    pdf_id = cursor.lastrowid

    for table_info in tables:
        cursor.execute("""
            INSERT INTO tables (pdf_id, page_num, table_index, rows, cols, category, company)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pdf_id,
            table_info['page_num'],
            table_info['table_index'],
            table_info['rows'],
            table_info['cols'],
            table_info['category'],
            table_info['company']
        ))

        table_id = cursor.lastrowid

        data = table_info['data']
        for row_idx, row in enumerate(data):
            is_header = 1 if row_idx == 0 else 0

            for col_idx, value in enumerate(row):
                cursor.execute("""
                    INSERT INTO table_data (table_id, row_idx, col_idx, value, is_header)
                    VALUES (?, ?, ?, ?, ?)
                """, (table_id, row_idx, col_idx, value, is_header))

                if is_header and value:
                    cursor.execute("""
                        INSERT OR IGNORE INTO table_headers (table_id, col_idx, header_name)
                        VALUES (?, ?, ?)
                    """, (table_id, col_idx, value))

        # 금융 모드: 정규화된 데이터 저장
        if financial_mode and table_info['company']:
            save_financial_data(cursor, table_id, table_info)

    conn.commit()
    print(f"저장 완료: {len(tables)}개 표 → {conn.total_changes} 레코드")


def save_financial_data(cursor: sqlite3.Cursor, table_id: int, table_info: dict):
    """금융 데이터 정규화 저장"""
    data = table_info['data']
    company = table_info['company']
    category = table_info['category']

    if not data or len(data) < 2:
        return

    # 회사 등록
    cursor.execute("INSERT OR IGNORE INTO companies (name) VALUES (?)", (company,))
    cursor.execute("SELECT id FROM companies WHERE name = ?", (company,))
    company_id = cursor.fetchone()[0]

    # 헤더에서 연도 추출
    header = data[0]
    year_cols = {}

    for col_idx, cell in enumerate(header):
        cell_str = str(cell)
        for year in range(2020, 2030):
            if str(year) in cell_str:
                is_estimate = 'E' in cell_str.upper()
                year_cols[col_idx] = (year, is_estimate)
                break

    if not year_cols:
        return

    # 데이터 행 처리
    for row in data[1:]:
        if not row:
            continue

        metric_name = clean_cell_value(row[0])
        if not metric_name:
            continue

        # 지표 등록 (단위 자동 할당)
        unit = get_metric_unit(metric_name)
        cursor.execute("""
            INSERT OR IGNORE INTO metrics (category, name_kor, unit)
            VALUES (?, ?, ?)
        """, (category, metric_name, unit))
        # 기존 지표의 단위가 없으면 업데이트
        if unit:
            cursor.execute("""
                UPDATE metrics SET unit = ? WHERE category = ? AND name_kor = ? AND unit IS NULL
            """, (unit, category, metric_name))
        cursor.execute("""
            SELECT id FROM metrics WHERE category = ? AND name_kor = ?
        """, (category, metric_name))
        metric_id = cursor.fetchone()[0]

        # 연도별 값 저장
        for col_idx, (year, is_estimate) in year_cols.items():
            if col_idx < len(row):
                value, _ = parse_numeric_value(row[col_idx])
                if value is not None:
                    cursor.execute("""
                        INSERT OR REPLACE INTO financial_data
                        (company_id, metric_id, year, is_estimate, value, source_table_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (company_id, metric_id, year, is_estimate, value, table_id))


# =============================================================================
# 조회 및 내보내기
# =============================================================================

def show_db_info(db_path: str):
    """DB 정보 출력"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"\n{'='*60}")
    print(f"데이터베이스: {db_path}")
    print(f"{'='*60}")

    cursor.execute("SELECT COUNT(*) FROM pdf_sources")
    pdf_count = cursor.fetchone()[0]
    print(f"\nPDF 소스: {pdf_count}개")

    cursor.execute("SELECT filename, total_pages, created_at FROM pdf_sources")
    for row in cursor.fetchall():
        print(f"  - {row[0]} ({row[1]}페이지) [{row[2]}]")

    cursor.execute("SELECT COUNT(*) FROM tables")
    table_count = cursor.fetchone()[0]
    print(f"\n추출된 표: {table_count}개")

    cursor.execute("""
        SELECT category, COUNT(*) FROM tables GROUP BY category ORDER BY COUNT(*) DESC
    """)
    for row in cursor.fetchall():
        print(f"  - {row[0] or '미분류'}: {row[1]}개")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM companies")
        company_count = cursor.fetchone()[0]
        print(f"\n회사 수: {company_count}개")

        cursor.execute("SELECT name FROM companies ORDER BY name")
        companies = [row[0] for row in cursor.fetchall()]
        print(f"  {', '.join(companies)}")

        cursor.execute("SELECT COUNT(*) FROM financial_data")
        data_count = cursor.fetchone()[0]
        print(f"\n재무 데이터 포인트: {data_count}개")

    conn.close()


def list_tables(db_path: str):
    """표 목록 출력"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.page_num, t.table_index, t.rows, t.cols,
               t.category, t.company, p.filename
        FROM tables t
        JOIN pdf_sources p ON t.pdf_id = p.id
        ORDER BY t.page_num, t.table_index
    """)

    print(f"\n{'ID':<5} {'페이지':<6} {'행x열':<8} {'카테고리':<12} {'회사':<15} {'소스'}")
    print("-" * 80)

    for row in cursor.fetchall():
        print(f"{row[0]:<5} {row[1]:<6} {row[3]}x{row[4]:<5} {row[5] or '-':<12} {row[6] or '-':<15} {row[7]}")

    conn.close()


def show_table(db_path: str, table_id: int):
    """특정 표 내용 출력"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.page_num, t.category, t.company, t.rows, t.cols
        FROM tables t WHERE t.id = ?
    """, (table_id,))

    info = cursor.fetchone()
    if not info:
        print(f"오류: 표 ID {table_id}를 찾을 수 없습니다.")
        return

    print(f"\n표 #{table_id}: 페이지 {info[0]}, {info[1] or '미분류'}, {info[2] or '회사 미상'}")
    print(f"크기: {info[3]}행 x {info[4]}열")
    print("-" * 60)

    cursor.execute("""
        SELECT row_idx, col_idx, value, is_header
        FROM table_data
        WHERE table_id = ?
        ORDER BY row_idx, col_idx
    """, (table_id,))

    rows_data = {}
    for row in cursor.fetchall():
        row_idx, col_idx, value, is_header = row
        if row_idx not in rows_data:
            rows_data[row_idx] = {}
        rows_data[row_idx][col_idx] = value

    for row_idx in sorted(rows_data.keys()):
        cols = rows_data[row_idx]
        values = [cols.get(i, '') for i in range(max(cols.keys()) + 1)]
        print(' | '.join(str(v)[:15].ljust(15) for v in values))

    conn.close()


def export_to_csv(db_path: str, output_dir: str, with_bom: bool = True):
    """CSV로 내보내기"""
    if pd is None:
        print("오류: pandas가 필요합니다. pip install pandas")
        return

    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, page_num, category, company FROM tables")
    tables = cursor.fetchall()

    for table_id, page_num, category, company in tables:
        cursor.execute("""
            SELECT row_idx, col_idx, value
            FROM table_data
            WHERE table_id = ?
            ORDER BY row_idx, col_idx
        """, (table_id,))

        rows_data = {}
        max_col = 0
        for row_idx, col_idx, value in cursor.fetchall():
            if row_idx not in rows_data:
                rows_data[row_idx] = {}
            rows_data[row_idx][col_idx] = value
            max_col = max(max_col, col_idx)

        data = []
        for row_idx in sorted(rows_data.keys()):
            row = [rows_data[row_idx].get(i, '') for i in range(max_col + 1)]
            data.append(row)

        df = pd.DataFrame(data)

        safe_category = (category or 'table').replace('/', '_')
        safe_company = (company or '').replace('/', '_')
        filename = f"table_{table_id}_p{page_num}_{safe_category}_{safe_company}.csv"
        filepath = os.path.join(output_dir, filename)

        encoding = 'utf-8-sig' if with_bom else 'utf-8'
        df.to_csv(filepath, index=False, header=False, encoding=encoding)
        print(f"내보내기: {filepath}")

    conn.close()
    print(f"\n총 {len(tables)}개 CSV 파일 생성됨")


def export_to_markdown(db_path: str, output_file: str):
    """마크다운으로 내보내기"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# PDF 표 추출 결과\n\n")
        f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        cursor.execute("""
            SELECT t.id, t.page_num, t.category, t.company, t.rows, t.cols
            FROM tables t
            ORDER BY t.page_num, t.table_index
        """)

        for table_id, page_num, category, company, rows, cols in cursor.fetchall():
            f.write(f"## 표 #{table_id}\n\n")
            f.write(f"- 페이지: {page_num}\n")
            f.write(f"- 카테고리: {category or '미분류'}\n")
            f.write(f"- 회사: {company or '-'}\n")
            f.write(f"- 크기: {rows}행 x {cols}열\n\n")

            cursor.execute("""
                SELECT row_idx, col_idx, value
                FROM table_data
                WHERE table_id = ?
                ORDER BY row_idx, col_idx
            """, (table_id,))

            rows_data = {}
            max_col = 0
            for row_idx, col_idx, value in cursor.fetchall():
                if row_idx not in rows_data:
                    rows_data[row_idx] = {}
                rows_data[row_idx][col_idx] = value
                max_col = max(max_col, col_idx)

            for row_idx in sorted(rows_data.keys()):
                cols_data = rows_data[row_idx]
                values = [cols_data.get(i, '') for i in range(max_col + 1)]
                f.write('| ' + ' | '.join(str(v) for v in values) + ' |\n')

                if row_idx == 0:
                    f.write('|' + '---|' * (max_col + 1) + '\n')

            f.write('\n---\n\n')

    conn.close()
    print(f"마크다운 내보내기 완료: {output_file}")


# =============================================================================
# 메인 함수
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='PDF 표 추출 및 SQLite DB 저장',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # PDF에서 표 추출
  python pdftable2db.py input.pdf output.db

  # 금융 보고서 모드
  python pdftable2db.py report.pdf report.db --financial

  # DB 정보 확인
  python pdftable2db.py output.db --info
        """
    )

    parser.add_argument('input', help='입력 PDF 파일 또는 DB 파일')
    parser.add_argument('output', nargs='?', help='출력 DB 파일 (추출 모드)')

    parser.add_argument('--pages', help='처리할 페이지 (예: "1-5", "1,3,5")')
    parser.add_argument('--financial', action='store_true', help='금융 보고서 모드')
    parser.add_argument('--min-rows', type=int, default=2, help='최소 행 수 (기본: 2)')

    parser.add_argument('--info', action='store_true', help='DB 정보 출력')
    parser.add_argument('--list-tables', action='store_true', help='표 목록 출력')
    parser.add_argument('--show-table', type=int, metavar='ID', help='특정 표 출력')

    parser.add_argument('--export-csv', metavar='DIR', help='CSV로 내보내기')
    parser.add_argument('--export-md', metavar='FILE', help='마크다운으로 내보내기')

    args = parser.parse_args()

    input_path = args.input

    # 조회/내보내기 모드
    if input_path.endswith('.db'):
        if not os.path.exists(input_path):
            print(f"오류: DB 파일을 찾을 수 없습니다: {input_path}")
            sys.exit(1)

        if args.info:
            show_db_info(input_path)
        elif args.list_tables:
            list_tables(input_path)
        elif args.show_table:
            show_table(input_path, args.show_table)
        elif args.export_csv:
            export_to_csv(input_path, args.export_csv)
        elif args.export_md:
            export_to_markdown(input_path, args.export_md)
        else:
            show_db_info(input_path)
        return

    # 추출 모드
    if not input_path.endswith('.pdf'):
        print(f"오류: PDF 파일이 아닙니다: {input_path}")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"오류: PDF 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    if not args.output:
        args.output = os.path.splitext(input_path)[0] + '_tables.db'

    print(f"PDF 표 추출 시작: {input_path}")
    print(f"출력 DB: {args.output}")

    with pdfplumber.open(input_path) as pdf:
        total_pages = len(pdf.pages)

    pages = parse_pages(args.pages, total_pages) if args.pages else None

    if pages:
        print(f"처리 페이지: {min(pages)+1} ~ {max(pages)+1}")
    else:
        print(f"전체 {total_pages} 페이지 처리")

    tables = extract_tables_from_pdf(input_path, pages, args.min_rows)
    print(f"추출된 표: {len(tables)}개")

    if not tables:
        print("경고: 추출된 표가 없습니다.")
        return

    # 기존 DB 삭제 후 새로 생성
    if os.path.exists(args.output):
        os.remove(args.output)

    conn = create_database(args.output, args.financial)
    save_to_database(conn, input_path, tables, args.financial)
    conn.close()

    print(f"\n완료! DB 저장됨: {args.output}")
    show_db_info(args.output)


if __name__ == '__main__':
    main()
