# -*- coding: utf-8 -*-
"""promo-query CLI 진입점

IBK 승진결과 데이터를 ibk_HR.db에서 추출하여 마크다운 테이블로 출력한다.

Usage:
    python promo_query.py <command> [options]

Commands:
    dates          승진년월 목록 조회
    summary        직급별 승진 요약 (대상자/승진자/승진률)
    by-group       그룹별 승진 현황
    by-branch      부점별/세분별 분포
    by-gender      성별 분석 (직급별)
    by-tenure      연차별 분석 (입행/직급)
    by-age         연령별 분석 (통계/분포/프로필)
    duration       소요기간 분석
    career-path    승진경로 + 본점경유 비율
    career-impact  과거 이력 영향 (본점경험/소속연차)
    compare        승진자 vs 미승진자 프로필 비교
    cross-tab      교차분석 (그룹x직급, 성별x직급, ...)
    timeline       시계열 추이 (최근 N회차)
    prev-compare   전회차/동월 YoY 비교
"""

import argparse
import sys
import os

# 패키지 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.executor import get_latest_date, validate_date, validate_filter
from queries.current import (
    query_summary, query_by_group, query_by_branch, query_by_gender,
    query_by_tenure, query_by_age, query_duration, query_career_path,
    query_career_impact, query_compare, query_cross_tab,
)
from queries.historical import (
    query_dates, query_timeline, query_prev_compare,
)


def create_parser():
    parser = argparse.ArgumentParser(
        description='IBK 승진결과 데이터 쿼리 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python promo_query.py dates
  python promo_query.py summary --date 202601
  python promo_query.py by-group --date 202601 --scope 그룹 --filter "디지털그룹" --include-total
  python promo_query.py timeline --date 202601
  python promo_query.py prev-compare --date 202601
""",
    )

    parser.add_argument('command', choices=[
        'dates', 'summary', 'by-group', 'by-branch', 'by-gender',
        'by-tenure', 'by-age', 'duration', 'career-path', 'career-impact',
        'compare', 'cross-tab', 'timeline', 'prev-compare',
    ], help='실행할 쿼리 명령')

    parser.add_argument('--date', type=str, default=None,
                        help='대상 승진년월 (YYYYMM). 미지정 시 최신.')
    parser.add_argument('--scope', type=str, default='전행',
                        choices=['전행', '그룹', '부점', '세분', '본점비교'],
                        help='분석 범위 (기본: 전행)')
    parser.add_argument('--filter', type=str, default=None,
                        help='범위 필터값 (그룹명/부점명 등)')
    parser.add_argument('--include-total', action='store_true',
                        help='전행 평균 비교 데이터 함께 출력')
    parser.add_argument('--limit', type=int, default=None,
                        help='TOP N 결과 (기본: 20)')
    parser.add_argument('--count', type=int, default=None,
                        help='시계열 회차 수 (기본: 10)')
    parser.add_argument('--format', type=str, default='markdown',
                        choices=['markdown', 'csv'],
                        help='출력 형식 (기본: markdown)')
    parser.add_argument('--db', type=str, default=None,
                        help='DB 경로 (override)')

    return parser


def main():
    # stdout UTF-8 강제 설정 (Windows 환경 대응)
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

    parser = create_parser()
    args = parser.parse_args()

    db_path = args.db
    command = args.command

    # dates 명령은 날짜 불필요
    if command == 'dates':
        print(query_dates(db_path=db_path))
        return

    # 날짜 결정
    if args.date:
        date, err = validate_date(args.date, db_path=db_path)
        if err:
            print(f'오류: {err}', file=sys.stderr)
            sys.exit(1)
    else:
        date = get_latest_date(db_path=db_path)
        if not date:
            print('오류: promotion_list에 데이터가 없습니다.', file=sys.stderr)
            sys.exit(1)

    # 범위 필터 검증
    if args.scope != '전행' and args.filter:
        valid, err = validate_filter(args.scope, args.filter, db_path=db_path)
        if not valid:
            print(f'오류: {err}', file=sys.stderr)
            sys.exit(1)

    # 공통 인자
    common = {
        'date': date,
        'scope': args.scope,
        'filter_value': args.filter,
        'db_path': db_path,
    }

    # 명령 라우팅
    if command == 'summary':
        print(query_summary(**common))
    elif command == 'by-group':
        print(query_by_group(**common, include_total=args.include_total))
    elif command == 'by-branch':
        print(query_by_branch(**common))
    elif command == 'by-gender':
        print(query_by_gender(**common))
    elif command == 'by-tenure':
        print(query_by_tenure(**common))
    elif command == 'by-age':
        print(query_by_age(**common))
    elif command == 'duration':
        print(query_duration(**common))
    elif command == 'career-path':
        print(query_career_path(**common, limit=args.limit))
    elif command == 'career-impact':
        print(query_career_impact(**common))
    elif command == 'compare':
        print(query_compare(**common))
    elif command == 'cross-tab':
        print(query_cross_tab(**common))
    elif command == 'timeline':
        print(query_timeline(date=date, count=args.count, db_path=db_path))
    elif command == 'prev-compare':
        print(query_prev_compare(date=date, db_path=db_path))


if __name__ == '__main__':
    main()
