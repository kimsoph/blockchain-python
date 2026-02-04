# -*- coding: utf-8 -*-
"""시계열 쿼리 12종

과거 승진 이력의 시계열 추이와 전회차/YoY 비교를 수행하는 쿼리 함수들이다.
"""

from core.config import (
    rank_order_sql, DEFAULT_TIMELINE_COUNT, DEFAULT_LIMIT,
)
from core.formatter import to_markdown_table, section_header
from db.executor import execute_query, execute_scalar


def _recent_dates_subquery(n):
    """최근 N회차 서브쿼리를 반환한다."""
    return f"(SELECT DISTINCT 승진년월 FROM promotion_list ORDER BY 승진년월 DESC LIMIT {n})"


# ──────────────────────────────────────────────
# dates: 승진년월 목록
# ──────────────────────────────────────────────
def query_dates(db_path=None):
    sql = """
    SELECT 승진년월, COUNT(*) AS 승진자수
    FROM promotion_list
    GROUP BY 승진년월
    ORDER BY 승진년월 DESC
    """
    headers = ['승진년월', '승진자수']
    _, rows = execute_query(sql, db_path=db_path)

    output = section_header('승진년월 목록')
    output += to_markdown_table(headers, rows)
    return output


# ──────────────────────────────────────────────
# timeline: 시계열 추이
# ──────────────────────────────────────────────
def query_timeline(date=None, count=None, db_path=None):
    count = count or DEFAULT_TIMELINE_COUNT
    output = section_header(f'시계열 추이 (최근 {count}회차)')

    # 1. 회차별 직급별 승진 인원
    sql_by_rank = f"""
    SELECT
      p.승진년월,
      p.승진직급,
      COUNT(*) AS 승진자수
    FROM promotion_list p
    WHERE p.승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY p.승진년월, p.승진직급
    ORDER BY p.승진년월 DESC,
      {rank_order_sql('p.승진직급')}
    """
    headers_rank = ['승진년월', '승진직급', '승진자수']
    _, rows_rank = execute_query(sql_by_rank, db_path=db_path)
    output += section_header('회차별 직급별 승진 인원', 3)
    output += to_markdown_table(headers_rank, rows_rank)

    # 2. 회차별 총 승진 인원
    sql_total = f"""
    SELECT
      승진년월,
      COUNT(*) AS 총승진자,
      SUM(CASE WHEN 승진직급 IN ('승0','승1','승2') THEN 1 ELSE 0 END) AS 고직급,
      SUM(CASE WHEN 승진직급 IN ('PCEO','승3','승4') THEN 1 ELSE 0 END) AS 저직급
    FROM promotion_list
    WHERE 승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY 승진년월
    ORDER BY 승진년월 DESC
    """
    headers_total = ['승진년월', '총승진자', '고직급(승0~승2)', '저직급(PCEO~승4)']
    _, rows_total = execute_query(sql_total, db_path=db_path)
    mapped_total = []
    for r in rows_total:
        mapped_total.append({
            '승진년월': r['승진년월'],
            '총승진자': r['총승진자'],
            '고직급(승0~승2)': r['고직급'],
            '저직급(PCEO~승4)': r['저직급'],
        })
    output += section_header('회차별 총 승진 인원', 3)
    output += to_markdown_table(headers_total, mapped_total)

    # 3. 회차별 소요기간 추이
    sql_dur = f"""
    SELECT
      p.승진년월,
      p.승진직급,
      ROUND(AVG(p.소요기간), 1) AS 평균소요기간,
      MIN(p.소요기간) AS 최소소요기간,
      MAX(p.소요기간) AS 최대소요기간
    FROM promotion_list p
    WHERE p.승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY p.승진년월, p.승진직급
    ORDER BY p.승진년월 DESC,
      {rank_order_sql('p.승진직급')}
    """
    headers_dur = ['승진년월', '승진직급', '평균소요기간', '최소소요기간', '최대소요기간']
    _, rows_dur = execute_query(sql_dur, db_path=db_path)
    output += section_header('회차별 소요기간 추이', 3)
    output += to_markdown_table(headers_dur, rows_dur)

    # 4. 회차별 성별 승진 추이
    sql_gender = f"""
    SELECT
      p.승진년월,
      h.성별,
      COUNT(*) AS 승진자수
    FROM promotion_list p
    JOIN HR h ON p.직번 = h.직번
    WHERE p.승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY p.승진년월, h.성별
    ORDER BY p.승진년월 DESC, h.성별
    """
    headers_gender = ['승진년월', '성별', '승진자수']
    _, rows_gender = execute_query(sql_gender, db_path=db_path)
    for r in rows_gender:
        r['성별'] = '남' if r['성별'] == 'M' else '여'
    output += section_header('회차별 성별 승진 추이', 3)
    output += to_markdown_table(headers_gender, rows_gender)

    # 5. 회차별 평균 승진 나이 추이
    sql_age = f"""
    SELECT
      p.승진년월,
      p.승진직급,
      COUNT(*) AS 승진자수,
      ROUND(AVG(h.현재나이), 1) AS 평균나이,
      MIN(h.현재나이) AS 최소나이,
      MAX(h.현재나이) AS 최대나이
    FROM promotion_list p
    JOIN HR h ON p.직번 = h.직번
    WHERE p.승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY p.승진년월, p.승진직급
    ORDER BY p.승진년월 DESC,
      {rank_order_sql('p.승진직급')}
    """
    headers_age = ['승진년월', '승진직급', '승진자수', '평균나이', '최소나이', '최대나이']
    _, rows_age = execute_query(sql_age, db_path=db_path)
    output += section_header('회차별 평균 승진 나이 추이', 3)
    output += to_markdown_table(headers_age, rows_age, count_col='승진자수')

    # 6. 회차별 본점/영업점 비율 추이
    sql_hq = f"""
    SELECT
      p.승진년월,
      h.본점여부,
      COUNT(*) AS 승진자수
    FROM promotion_list p
    JOIN HR h ON p.직번 = h.직번
    WHERE p.승진년월 IN {_recent_dates_subquery(count)}
    GROUP BY p.승진년월, h.본점여부
    ORDER BY p.승진년월 DESC
    """
    headers_hq = ['승진년월', '구분', '승진자수']
    _, rows_hq = execute_query(sql_hq, db_path=db_path)
    mapped_hq = []
    for r in rows_hq:
        mapped_hq.append({
            '승진년월': r['승진년월'],
            '구분': '본점' if r['본점여부'] else '영업점',
            '승진자수': r['승진자수'],
        })
    output += section_header('회차별 본점/영업점 비율 추이', 3)
    output += to_markdown_table(headers_hq, mapped_hq)

    # 7. 회차별 주요 승진부점 (최근 5회차, 각 TOP 10)
    sql_branch = f"""
    SELECT
      p.승진년월,
      p.승진부점,
      COUNT(*) AS 승진자수
    FROM promotion_list p
    WHERE p.승진년월 IN (SELECT DISTINCT 승진년월 FROM promotion_list ORDER BY 승진년월 DESC LIMIT 5)
    GROUP BY p.승진년월, p.승진부점
    ORDER BY p.승진년월 DESC, 승진자수 DESC
    """
    headers_branch = ['승진년월', '승진부점', '승진자수']
    _, rows_branch = execute_query(sql_branch, db_path=db_path)
    # 회차별 TOP 10만 필터링
    from collections import defaultdict
    branch_count = defaultdict(int)
    filtered_branch = []
    for r in rows_branch:
        key = r['승진년월']
        branch_count[key] += 1
        if branch_count[key] <= 10:
            filtered_branch.append(r)
    output += section_header('회차별 주요 승진부점 (TOP 10)', 3)
    output += to_markdown_table(headers_branch, filtered_branch)

    return output


# ──────────────────────────────────────────────
# prev-compare: 전회차/동월 YoY 비교
# ──────────────────────────────────────────────
def query_prev_compare(date, db_path=None):
    output = section_header(f'전회차/동월 YoY 비교 ({date})')

    # 전회차 식별
    prev_date = execute_scalar(
        f"SELECT MAX(승진년월) FROM promotion_list WHERE 승진년월 < {date}",
        db_path=db_path
    )

    # 동월 YoY 식별 (약 12개월 전 가장 가까운 회차)
    yoy_date = execute_scalar(
        f"""SELECT 승진년월 FROM promotion_list
        WHERE 승진년월 BETWEEN {date} - 102 AND {date} - 98
        GROUP BY 승진년월
        ORDER BY ABS(승진년월 - ({date} - 100)) ASC LIMIT 1""",
        db_path=db_path
    )

    if not prev_date and not yoy_date:
        output += '_비교 데이터 없음_\n'
        return output

    # 비교 대상 회차 정보
    output += f'- 현재 회차: {date}\n'
    if prev_date:
        output += f'- 전회차: {prev_date}\n'
    if yoy_date:
        output += f'- 전년 동월: {yoy_date}\n'
    output += '\n'

    # 직급별 비교 테이블
    compare_dates = [date]
    date_labels = [str(date)]
    if prev_date:
        compare_dates.append(prev_date)
        date_labels.append(f'{prev_date}(전회차)')
    if yoy_date and yoy_date != prev_date:
        compare_dates.append(yoy_date)
        date_labels.append(f'{yoy_date}(YoY)')

    for i, comp_date in enumerate(compare_dates):
        sql = f"""
        SELECT
          p.승진직급,
          COUNT(*) AS 승진자수,
          ROUND(AVG(p.소요기간), 1) AS 평균소요기간
        FROM promotion_list p
        WHERE p.승진년월 = {comp_date}
        GROUP BY p.승진직급
        ORDER BY {rank_order_sql('p.승진직급')}
        """
        headers = ['승진직급', '승진자수', '평균소요기간']
        _, rows = execute_query(sql, db_path=db_path)
        output += section_header(f'{date_labels[i]}', 3)
        output += to_markdown_table(headers, rows, count_col='승진자수')

    # 총계 비교
    output += section_header('총계 비교', 3)
    summary_headers = ['항목'] + date_labels
    summary_rows = []

    totals = []
    for comp_date in compare_dates:
        total = execute_scalar(
            f"SELECT COUNT(*) FROM promotion_list WHERE 승진년월 = {comp_date}",
            db_path=db_path
        )
        totals.append(total or 0)

    row_total = {'항목': '총 승진자'}
    for i, label in enumerate(date_labels):
        row_total[label] = totals[i]
    summary_rows.append(row_total)

    # 증감
    if len(totals) >= 2 and totals[0] and totals[1]:
        diff = totals[0] - totals[1]
        pct = round(diff * 100.0 / totals[1], 1)
        row_diff = {'항목': '전회차 대비'}
        row_diff[date_labels[0]] = f'{diff:+d} ({pct:+.1f}%)'
        row_diff[date_labels[1]] = '-'
        if len(date_labels) > 2:
            row_diff[date_labels[2]] = '-'
        summary_rows.append(row_diff)

    if len(totals) >= 3 and totals[0] and totals[2]:
        diff = totals[0] - totals[2]
        pct = round(diff * 100.0 / totals[2], 1)
        row_yoy = {'항목': 'YoY 대비'}
        row_yoy[date_labels[0]] = f'{diff:+d} ({pct:+.1f}%)'
        row_yoy[date_labels[1]] = '-'
        row_yoy[date_labels[2]] = '-'
        summary_rows.append(row_yoy)

    output += to_markdown_table(summary_headers, summary_rows)

    return output
