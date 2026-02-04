# -*- coding: utf-8 -*-
"""마크다운 테이블 포매터

쿼리 결과를 마크다운 테이블로 변환하며, 숫자 포매팅과 소수집단 플래그를 처리한다.
"""

from core.config import MIN_GROUP_SIZE

# 콤마 포매팅을 하지 않는 컬럼명 (YYYYMM 등 코드성 숫자)
NO_COMMA_COLUMNS = {'승진년월', '출생년월', '입행년월', '임피년월', '직위년월', '소속년월', '나이대'}


def format_number(value, decimals=None, no_comma=False):
    """숫자를 읽기 좋게 포매팅한다.

    - None/빈값 -> '-'
    - 정수 -> 천 단위 콤마 (no_comma=True이면 콤마 없이)
    - 실수 -> 소수점 이하 지정 자릿수
    """
    if value is None:
        return '-'
    if isinstance(value, str):
        return value
    if no_comma:
        if decimals is not None:
            return f'{value:.{decimals}f}'
        if isinstance(value, float):
            if value == int(value):
                return str(int(value))
            return f'{value:.1f}'
        return str(value)
    if decimals is not None:
        return f'{value:,.{decimals}f}'
    if isinstance(value, float):
        if value == int(value):
            return f'{int(value):,}'
        return f'{value:,.1f}'
    return f'{value:,}'


def to_markdown_table(headers, rows, alignments=None, note=None,
                      count_col=None, flag_small=True):
    """딕셔너리 리스트 또는 튜플 리스트를 마크다운 테이블로 변환한다.

    Args:
        headers: 컬럼 이름 리스트
        rows: 딕셔너리 리스트 또는 튜플/리스트의 리스트
        alignments: 정렬 리스트 ('l', 'r', 'c'). None이면 자동 판별.
        note: 테이블 아래 부가 설명
        count_col: 소수집단 플래그를 적용할 인원 컬럼 이름 (str) 또는 인덱스 (int)
        flag_small: 소수집단 플래그 활성화 여부
    """
    if not rows:
        return '_데이터 없음_\n'

    # rows가 딕셔너리 리스트인 경우 -> 튜플 리스트로 변환
    if isinstance(rows[0], dict):
        tuple_rows = [tuple(row.get(h, None) for h in headers) for row in rows]
    else:
        tuple_rows = [tuple(r) for r in rows]

    # 컬럼별 no_comma 판별
    no_comma_flags = [h in NO_COMMA_COLUMNS for h in headers]

    # 자동 정렬: 숫자 -> 오른쪽, 문자 -> 왼쪽
    if alignments is None:
        alignments = []
        for i, h in enumerate(headers):
            sample_vals = [r[i] for r in tuple_rows if r[i] is not None][:5]
            if sample_vals and all(isinstance(v, (int, float)) for v in sample_vals):
                alignments.append('r')
            else:
                alignments.append('l')

    # 포매팅
    formatted_rows = []
    small_group_indices = set()
    for row_idx, row in enumerate(tuple_rows):
        formatted = []
        for col_idx, val in enumerate(row):
            formatted.append(format_number(val, no_comma=no_comma_flags[col_idx]))
        formatted_rows.append(formatted)

        # 소수집단 체크
        if flag_small and count_col is not None:
            if isinstance(count_col, str):
                ci = headers.index(count_col) if count_col in headers else None
            else:
                ci = count_col
            if ci is not None and row[ci] is not None:
                if isinstance(row[ci], (int, float)) and row[ci] < MIN_GROUP_SIZE:
                    small_group_indices.add(row_idx)

    # 컬럼 너비 계산 (display_width 기준)
    def display_width(s):
        w = 0
        for ch in s:
            if '\uac00' <= ch <= '\ud7a3' or '\u4e00' <= ch <= '\u9fff':
                w += 2
            else:
                w += 1
        return w

    col_widths = [display_width(h) for h in headers]
    for row in formatted_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], display_width(cell))

    def pad(s, width, align='l'):
        dw = display_width(s)
        needed = max(0, width - dw)
        if align == 'r':
            return ' ' * needed + s
        elif align == 'c':
            left = needed // 2
            right = needed - left
            return ' ' * left + s + ' ' * right
        return s + ' ' * needed

    # 헤더 행
    lines = []
    header_cells = [pad(h, col_widths[i], alignments[i]) for i, h in enumerate(headers)]
    lines.append('| ' + ' | '.join(header_cells) + ' |')

    # 구분선
    sep_cells = []
    for i, a in enumerate(alignments):
        w = max(col_widths[i], 3)
        if a == 'r':
            sep_cells.append('-' * (w - 1) + ':')
        elif a == 'c':
            sep_cells.append(':' + '-' * (w - 2) + ':')
        else:
            sep_cells.append('-' * w)
    lines.append('| ' + ' | '.join(sep_cells) + ' |')

    # 데이터 행
    for row_idx, row in enumerate(formatted_rows):
        cells = [pad(cell, col_widths[i], alignments[i]) for i, cell in enumerate(row)]
        line = '| ' + ' | '.join(cells) + ' |'
        if row_idx in small_group_indices:
            line += ' *'
        lines.append(line)

    result = '\n'.join(lines) + '\n'

    # 소수집단 주석
    if small_group_indices:
        result += f'\n> *\\* {MIN_GROUP_SIZE}명 미만 소수집단 - 해석 주의*\n'

    if note:
        result += f'\n> *{note}*\n'

    return result


def format_total_row(headers, row_data, bold=True):
    """합계 행을 포매팅한다. bold=True이면 볼드 처리."""
    if bold:
        return {h: f'**{format_number(v)}**' if v is not None else '**-**'
                for h, v in zip(headers, row_data)}
    return {h: format_number(v) for h, v in zip(headers, row_data)}


def section_header(title, level=2):
    """마크다운 섹션 헤더를 반환한다."""
    return f'{"#" * level} {title}\n'
