# -*- coding: utf-8 -*-
"""현황 쿼리 12종

특정 승진년월의 스냅샷 데이터를 추출하는 쿼리 함수들이다.
모든 쿼리는 config.py의 상수를 참조하여 서열, 필터 등을 일관되게 적용한다.
"""

from core.config import (
    rank_order_sql, BASE_FILTER, TARGET_FILTER,
    SCOPE_COLUMN_MAP, DEFAULT_LIMIT,
)
from core.formatter import to_markdown_table, section_header
from db.executor import execute_query


def _scope_filter(scope, filter_value):
    """범위 필터 SQL 조건절을 생성한다."""
    if scope == '전행' or not filter_value:
        return ''
    col = SCOPE_COLUMN_MAP.get(scope)
    if col:
        return f" AND {col} = '{filter_value}'"
    return ''


def _left_join_promo(date):
    """promotion_list LEFT JOIN SQL을 생성한다."""
    return f"LEFT JOIN promotion_list p ON h.직번 = p.직번 AND p.승진년월 = {date}"


def _inner_join_promo(date):
    """promotion_list INNER JOIN SQL을 생성한다."""
    return f"JOIN promotion_list p ON h.직번 = p.직번 AND p.승진년월 = {date}"


# ──────────────────────────────────────────────
# 1. 직급별 승진 현황 (summary)
# ──────────────────────────────────────────────
def query_summary(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      h.승진직급,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}
    """
    headers = ['승진직급', '대상자', '승진자', '승진률(%)']
    cols, rows = execute_query(sql, db_path=db_path)

    # 합계 행
    total_target = sum(r['대상자'] for r in rows)
    total_promo = sum(r['승진자'] for r in rows)
    total_rate = round(total_promo * 100.0 / total_target, 1) if total_target else 0
    rows.append({
        '승진직급': '**합계**',
        '대상자': total_target,
        '승진자': total_promo,
        '승진률': total_rate,
    })

    # 컬럼 이름 매핑
    mapped = []
    for r in rows:
        mapped.append({
            '승진직급': r.get('승진직급', ''),
            '대상자': r.get('대상자', 0),
            '승진자': r.get('승진자', 0),
            '승진률(%)': r.get('승진률', 0),
        })

    output = section_header(f'직급별 승진 현황 ({date})')
    output += to_markdown_table(headers, mapped, count_col='대상자')
    return output


# ──────────────────────────────────────────────
# 2. 그룹별 승진 현황 (by-group)
# ──────────────────────────────────────────────
def query_by_group(date, scope='전행', filter_value=None, include_total=False, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      h.그룹,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.그룹
    ORDER BY 승진률 DESC
    """
    headers = ['그룹', '대상자', '승진자', '승진률(%)']
    cols, rows = execute_query(sql, db_path=db_path)

    mapped = []
    for r in rows:
        mapped.append({
            '그룹': r['그룹'] or '(미지정)',
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })

    title = f'그룹별 승진 현황 ({date})'
    if filter_value and scope == '그룹':
        title = f'{filter_value} 승진 현황 ({date})'

    output = section_header(title)

    if include_total and filter_value:
        # 전행 평균도 함께 조회
        sql_total = f"""
        SELECT
          ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 전행승진률
        FROM HR h
        {_left_join_promo(date)}
        WHERE {TARGET_FILTER}
        """
        _, total_rows = execute_query(sql_total, db_path=db_path)
        if total_rows:
            total_rate = total_rows[0].get('전행승진률', 0)
            output += f'> *전행 평균 승진률: {total_rate}%*\n\n'

    output += to_markdown_table(headers, mapped, count_col='대상자')
    return output


# ──────────────────────────────────────────────
# 3. 부점별/세분별 분포 (by-branch)
# ──────────────────────────────────────────────
def query_by_branch(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      h.세분, h.본점여부,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.세분, h.본점여부
    ORDER BY 승진률 DESC
    """
    headers = ['세분', '본점여부', '대상자', '승진자', '승진률(%)']
    cols, rows = execute_query(sql, db_path=db_path)

    mapped = []
    for r in rows:
        mapped.append({
            '세분': r['세분'] or '(미지정)',
            '본점여부': '본점' if r['본점여부'] else '영업점',
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })

    output = section_header(f'부점별/세분별 분포 ({date})')
    output += to_markdown_table(headers, mapped, count_col='대상자')
    return output


# ──────────────────────────────────────────────
# 4. 성별 분석 (by-gender)
# ──────────────────────────────────────────────
def query_by_gender(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      h.승진직급, h.성별,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.승진직급, h.성별
    ORDER BY {rank_order_sql('h.승진직급')}, h.성별
    """
    headers = ['승진직급', '성별', '대상자', '승진자', '승진률(%)']
    cols, rows = execute_query(sql, db_path=db_path)

    mapped = []
    for r in rows:
        mapped.append({
            '승진직급': r['승진직급'],
            '성별': '남' if r['성별'] == 'M' else '여',
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })

    output = section_header(f'성별 분석 ({date})')
    output += to_markdown_table(headers, mapped, count_col='대상자')
    return output


# ──────────────────────────────────────────────
# 5. 연차별 분석 (by-tenure)
# ──────────────────────────────────────────────
def query_by_tenure(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      h.승진직급,
      ROUND(AVG(h.입행연차), 1) AS 평균입행연차,
      MIN(h.입행연차) AS 최소입행연차,
      MAX(h.입행연차) AS 최대입행연차,
      ROUND(AVG(h.직급연차), 1) AS 평균직급연차,
      MIN(h.직급연차) AS 최소직급연차,
      MAX(h.직급연차) AS 최대직급연차
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}
    """
    headers = ['승진직급', '평균입행연차', '최소입행연차', '최대입행연차',
               '평균직급연차', '최소직급연차', '최대직급연차']
    cols, rows = execute_query(sql, db_path=db_path)

    output = section_header(f'연차별 분석 ({date})')
    output += to_markdown_table(headers, rows)
    return output


# ──────────────────────────────────────────────
# 6. 연령별 분석 (by-age)
# ──────────────────────────────────────────────
def query_by_age(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    output = section_header(f'연령별 분석 ({date})')

    # 6.1 직급별 승진자 나이 통계
    sql_stats = f"""
    SELECT
      h.승진직급,
      COUNT(*) AS 승진자수,
      ROUND(AVG(h.현재나이), 1) AS 평균나이,
      MIN(h.현재나이) AS 최소나이,
      MAX(h.현재나이) AS 최대나이,
      ROUND(AVG(h.현재나이) - (
        SELECT AVG(h2.현재나이) FROM HR h2
        WHERE h2.인원포함여부=1 AND h2.승진대상여부=1 AND h2.승진직급=h.승진직급
      ), 1) AS 전체평균대비
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}
    """
    headers_stats = ['승진직급', '승진자수', '평균나이', '최소나이', '최대나이', '전체평균대비']
    _, rows_stats = execute_query(sql_stats, db_path=db_path)
    output += section_header('직급별 나이 통계', 3)
    output += to_markdown_table(headers_stats, rows_stats, count_col='승진자수')

    # 6.2 나이대별(5세 구간) 분포
    sql_dist = f"""
    SELECT
      h.승진직급,
      CAST(h.현재나이 / 5 AS INTEGER) * 5 AS 나이대,
      COUNT(*) AS 인원수
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진직급, 나이대
    ORDER BY {rank_order_sql('h.승진직급')}, 나이대
    """
    headers_dist = ['승진직급', '나이대', '인원수']
    _, rows_dist = execute_query(sql_dist, db_path=db_path)
    # 나이대 표시 변환
    for r in rows_dist:
        age = r['나이대']
        r['나이대'] = f'{age}~{age+4}세'
    output += section_header('나이대별 분포', 3)
    output += to_markdown_table(headers_dist, rows_dist, count_col='인원수')

    # 6.3 최연소/최고령 승진자 프로필 (이름 제외)
    sql_youngest = f"""
    SELECT
      h.승진직급, h.현재나이, h.입행연차, h.직급연차, h.그룹, h.세분
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    ORDER BY h.현재나이 ASC LIMIT 5
    """
    headers_profile = ['승진직급', '현재나이', '입행연차', '직급연차', '그룹', '세분']
    _, rows_youngest = execute_query(sql_youngest, db_path=db_path)
    output += section_header('최연소 승진자 (TOP 5)', 3)
    output += to_markdown_table(headers_profile, rows_youngest)

    sql_oldest = f"""
    SELECT
      h.승진직급, h.현재나이, h.입행연차, h.직급연차, h.그룹, h.세분
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    ORDER BY h.현재나이 DESC LIMIT 5
    """
    _, rows_oldest = execute_query(sql_oldest, db_path=db_path)
    output += section_header('최고령 승진자 (TOP 5)', 3)
    output += to_markdown_table(headers_profile, rows_oldest)

    return output


# ──────────────────────────────────────────────
# 7. 소요기간 분석 (duration)
# ──────────────────────────────────────────────
def query_duration(date, scope='전행', filter_value=None, db_path=None):
    sf = ''
    if scope != '전행' and filter_value:
        col = SCOPE_COLUMN_MAP.get(scope)
        if col:
            # 소요기간은 promotion_list 중심이므로 HR JOIN 필요
            sf = f" AND h.{col.split('.')[-1]} = '{filter_value}'"

    sql = f"""
    SELECT
      p.승진직급,
      COUNT(*) AS 승진자수,
      ROUND(AVG(p.소요기간), 1) AS 평균소요기간,
      MIN(p.소요기간) AS 최소소요기간,
      MAX(p.소요기간) AS 최대소요기간
    FROM promotion_list p
    LEFT JOIN HR h ON p.직번 = h.직번
    WHERE p.승진년월 = {date}{sf}
    GROUP BY p.승진직급
    ORDER BY {rank_order_sql('p.승진직급')}
    """
    headers = ['승진직급', '승진자수', '평균소요기간', '최소소요기간', '최대소요기간']
    _, rows = execute_query(sql, db_path=db_path)

    output = section_header(f'소요기간 분석 ({date})')
    output += to_markdown_table(headers, rows, count_col='승진자수')
    return output


# ──────────────────────────────────────────────
# 8. 승진경로 분석 (career-path)
# ──────────────────────────────────────────────
def query_career_path(date, scope='전행', filter_value=None, limit=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    limit = limit or DEFAULT_LIMIT
    output = section_header(f'승진경로 분석 ({date})')

    # 8.1 상위 승진경로 패턴
    sql_path = f"""
    SELECT
      h.승진경로, COUNT(*) AS 인원수
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진경로
    ORDER BY 인원수 DESC LIMIT {limit}
    """
    headers_path = ['승진경로', '인원수']
    _, rows_path = execute_query(sql_path, db_path=db_path)
    output += section_header(f'주요 경로 패턴 (TOP {limit})', 3)
    output += to_markdown_table(headers_path, rows_path, count_col='인원수')

    # 8.2 본점 경유 비율
    sql_hq = f"""
    SELECT
      h.승진직급,
      COUNT(*) AS 전체,
      SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END) AS 본점경유,
      ROUND(SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 본점경유율
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}
    """
    headers_hq = ['승진직급', '전체', '본점경유', '본점경유율(%)']
    _, rows_hq = execute_query(sql_hq, db_path=db_path)
    mapped_hq = []
    for r in rows_hq:
        mapped_hq.append({
            '승진직급': r['승진직급'],
            '전체': r['전체'],
            '본점경유': r['본점경유'],
            '본점경유율(%)': r['본점경유율'],
        })
    output += section_header('본점 경유 비율', 3)
    output += to_markdown_table(headers_hq, mapped_hq)

    return output


# ──────────────────────────────────────────────
# 9. 과거 이력 영향 (career-impact)
# ──────────────────────────────────────────────
def query_career_impact(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    output = section_header(f'과거 이력 영향 분석 ({date})')

    # 9.1 본점 경험과 승진률
    sql_hq_impact = f"""
    SELECT
      '승진자' AS 구분,
      COUNT(*) AS 인원수,
      SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END) AS 본점경험자,
      ROUND(SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 본점경험비율
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    UNION ALL
    SELECT
      '미승진자',
      COUNT(*),
      SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END),
      ROUND(SUM(CASE WHEN h.승진부점경로 LIKE '%본점%' OR h.승진부점경로 LIKE '%본영%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf} AND p.직번 IS NULL
    """
    headers_hq = ['구분', '인원수', '본점경험자', '본점경험비율(%)']
    _, rows_hq = execute_query(sql_hq_impact, db_path=db_path)
    mapped_hq = []
    for r in rows_hq:
        mapped_hq.append({
            '구분': r['구분'],
            '인원수': r['인원수'],
            '본점경험자': r['본점경험자'],
            '본점경험비율(%)': r['본점경험비율'],
        })
    output += section_header('본점 경험과 승진률', 3)
    output += to_markdown_table(headers_hq, mapped_hq)

    # 9.2 소속연차와 승진
    sql_tenure = f"""
    SELECT
      h.승진직급,
      ROUND(AVG(h.소속연차), 1) AS 평균소속연차
    FROM HR h
    {_inner_join_promo(date)}
    WHERE {BASE_FILTER}{sf}
    GROUP BY h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}
    """
    headers_tenure = ['승진직급', '평균소속연차']
    _, rows_tenure = execute_query(sql_tenure, db_path=db_path)
    output += section_header('소속연차와 승진', 3)
    output += to_markdown_table(headers_tenure, rows_tenure)

    return output


# ──────────────────────────────────────────────
# 10. 승진자 vs 미승진자 프로필 비교 (compare)
# ──────────────────────────────────────────────
def query_compare(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    sql = f"""
    SELECT
      CASE WHEN p.직번 IS NOT NULL THEN '승진자' ELSE '미승진자' END AS 구분,
      h.승진직급,
      COUNT(*) AS 인원수,
      ROUND(AVG(h.현재나이), 1) AS 평균나이,
      ROUND(AVG(h.입행연차), 1) AS 평균입행연차,
      ROUND(AVG(h.직급연차), 1) AS 평균직급연차,
      ROUND(AVG(h.소속연차), 1) AS 평균소속연차,
      ROUND(SUM(h.남성여부) * 100.0 / COUNT(*), 1) AS 남성비율,
      ROUND(SUM(h.본점여부) * 100.0 / COUNT(*), 1) AS 본점비율
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY 구분, h.승진직급
    ORDER BY {rank_order_sql('h.승진직급')}, 구분
    """
    headers = ['구분', '승진직급', '인원수', '평균나이', '평균입행연차',
               '평균직급연차', '평균소속연차', '남성비율(%)', '본점비율(%)']
    cols, rows = execute_query(sql, db_path=db_path)

    mapped = []
    for r in rows:
        mapped.append({
            '구분': r['구분'],
            '승진직급': r['승진직급'],
            '인원수': r['인원수'],
            '평균나이': r['평균나이'],
            '평균입행연차': r['평균입행연차'],
            '평균직급연차': r['평균직급연차'],
            '평균소속연차': r['평균소속연차'],
            '남성비율(%)': r['남성비율'],
            '본점비율(%)': r['본점비율'],
        })

    output = section_header(f'승진자 vs 미승진자 프로필 비교 ({date})')
    output += to_markdown_table(headers, mapped, count_col='인원수')
    return output


# ──────────────────────────────────────────────
# 11. 교차분석 (cross-tab)
# ──────────────────────────────────────────────
def query_cross_tab(date, scope='전행', filter_value=None, db_path=None):
    sf = _scope_filter(scope, filter_value)
    output = section_header(f'교차분석 ({date})')

    # 11.1 그룹 x 직급
    sql_group = f"""
    SELECT h.그룹, h.승진직급,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.그룹, h.승진직급
    ORDER BY h.그룹, {rank_order_sql('h.승진직급')}
    """
    headers_group = ['그룹', '승진직급', '대상자', '승진자', '승진률(%)']
    _, rows_group = execute_query(sql_group, db_path=db_path)
    mapped_g = []
    for r in rows_group:
        mapped_g.append({
            '그룹': r['그룹'] or '(미지정)',
            '승진직급': r['승진직급'],
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })
    output += section_header('그룹 x 직급', 3)
    output += to_markdown_table(headers_group, mapped_g, count_col='대상자')

    # 11.2 본점/영업점 x 직급
    sql_hq = f"""
    SELECT h.본점여부, h.승진직급,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.본점여부, h.승진직급
    ORDER BY h.본점여부, {rank_order_sql('h.승진직급')}
    """
    headers_hq = ['구분', '승진직급', '대상자', '승진자', '승진률(%)']
    _, rows_hq = execute_query(sql_hq, db_path=db_path)
    mapped_hq = []
    for r in rows_hq:
        mapped_hq.append({
            '구분': '본점' if r['본점여부'] else '영업점',
            '승진직급': r['승진직급'],
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })
    output += section_header('본점/영업점 x 직급', 3)
    output += to_markdown_table(headers_hq, mapped_hq, count_col='대상자')

    # 11.3 성별 x 직급 (by-gender에서도 출력하지만, 교차분석 섹션에서도 포함)
    sql_gender = f"""
    SELECT h.성별, h.승진직급,
      COUNT(*) AS 대상자,
      SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) AS 승진자,
      ROUND(SUM(CASE WHEN p.직번 IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 승진률
    FROM HR h
    {_left_join_promo(date)}
    WHERE {TARGET_FILTER}{sf}
    GROUP BY h.성별, h.승진직급
    ORDER BY h.성별, {rank_order_sql('h.승진직급')}
    """
    headers_gender = ['성별', '승진직급', '대상자', '승진자', '승진률(%)']
    _, rows_gender = execute_query(sql_gender, db_path=db_path)
    mapped_gd = []
    for r in rows_gender:
        mapped_gd.append({
            '성별': '남' if r['성별'] == 'M' else '여',
            '승진직급': r['승진직급'],
            '대상자': r['대상자'],
            '승진자': r['승진자'],
            '승진률(%)': r['승진률'],
        })
    output += section_header('성별 x 직급', 3)
    output += to_markdown_table(headers_gender, mapped_gd, count_col='대상자')

    return output
