#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_analyzer.py - IBK textBook DB 분석 모듈

ibk_textbook.db에서 경영지표를 조회하고 다기간 비교 분석을 수행합니다.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
import re

from metric_parser import MetricParser, extract_period_from_filename, format_period


class TextbookDBAnalyzer:
    """IBK textBook DB 분석 클래스"""

    def __init__(self, db_path: str):
        """
        DB 연결 초기화

        Args:
            db_path: SQLite DB 파일 경로
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"DB 파일을 찾을 수 없습니다: {db_path}\n"
                f"예상 경로: 3_Resources/R-about_ibk/outputs/ibk_textbook.db"
            )

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.parser = MetricParser()

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_available_periods(self) -> List[str]:
        """
        DB에 저장된 모든 기간 목록 조회

        Returns:
            기간 문자열 목록 (예: ['202403', '202406', ...])
        """
        cursor = self.conn.execute(
            "SELECT DISTINCT filename FROM documents ORDER BY filename"
        )
        periods = []
        for row in cursor:
            period = extract_period_from_filename(row['filename'])
            if period:
                periods.append(period)
        return periods

    def get_metric_trend(self, metric_name: str, periods: List[str] = None) -> Dict[str, Any]:
        """
        특정 지표의 다기간 추이 조회

        Args:
            metric_name: 지표명 (예: 'ROA', '당기순이익')
            periods: 조회할 기간 목록 (None이면 전체)

        Returns:
            {
                'metric': str,
                'labels': List[str],
                'values': List[float],
                'units': List[str]
            }
        """
        if periods is None:
            periods = self.get_available_periods()

        labels = []
        values = []
        units = []

        for period in periods:
            # 해당 기간의 문서에서 지표 검색
            cursor = self.conn.execute("""
                SELECT b.content
                FROM blocks b
                JOIN sections s ON b.section_id = s.id
                JOIN documents d ON s.document_id = d.id
                WHERE d.filename LIKE ?
                AND b.content LIKE ?
            """, (f'%{period}%', f'%{metric_name}%'))

            for row in cursor:
                result = self.parser.extract_metric(row['content'], metric_name)
                if result:
                    labels.append(format_period(period))
                    values.append(result['value'])
                    units.append(result['unit'])
                    break  # 첫 번째 매칭만 사용

        return {
            'metric': metric_name,
            'labels': labels,
            'values': values,
            'units': units[0] if units else '%'
        }

    def compare_periods(self, metric_name: str, period1: str, period2: str) -> Dict[str, Any]:
        """
        두 시점 간 지표 비교

        Args:
            metric_name: 지표명
            period1: 비교 기준 기간 (이전)
            period2: 비교 대상 기간 (현재)

        Returns:
            {
                'metric': str,
                'prev': {'period': str, 'value': float, 'unit': str},
                'current': {'period': str, 'value': float, 'unit': str},
                'change': float,
                'change_pct': float
            }
        """
        trend = self.get_metric_trend(metric_name, [period1, period2])

        if len(trend['values']) < 2:
            return {
                'metric': metric_name,
                'prev': None,
                'current': None,
                'change': None,
                'change_pct': None,
                'error': '데이터 부족'
            }

        prev_value = trend['values'][0]
        curr_value = trend['values'][1]
        change = curr_value - prev_value
        change_pct = (change / prev_value * 100) if prev_value != 0 else 0

        return {
            'metric': metric_name,
            'prev': {
                'period': format_period(period1),
                'value': prev_value,
                'unit': trend['units']
            },
            'current': {
                'period': format_period(period2),
                'value': curr_value,
                'unit': trend['units']
            },
            'change': round(change, 4),
            'change_pct': round(change_pct, 2)
        }

    def generate_comparison_chart(self, metrics: List[str], periods: List[str]) -> Dict[str, Any]:
        """
        다기간 비교 차트 데이터 생성 (make-chart 스킬 호환)

        Args:
            metrics: 지표명 목록
            periods: 기간 목록

        Returns:
            make-chart 스킬에 전달 가능한 dict
            {
                'labels': List[str],
                'series': [{'name': str, 'values': List[float]}, ...]
            }
        """
        labels = [format_period(p) for p in periods]
        series = []

        for metric in metrics:
            trend = self.get_metric_trend(metric, periods)
            series.append({
                'name': f"{metric}({trend['units']})",
                'values': trend['values']
            })

        return {
            'labels': labels,
            'series': series
        }

    def extract_chapter_metrics(self, period: str, chapter_num: int) -> List[Dict[str, Any]]:
        """
        특정 기간/챕터의 모든 지표 추출

        Args:
            period: 기간 (예: '202510')
            chapter_num: 챕터 번호 (1-9)

        Returns:
            추출된 지표 목록
        """
        # 로마 숫자 매핑
        roman_numerals = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
            6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX'
        }
        roman = roman_numerals.get(chapter_num, str(chapter_num))

        # 해당 챕터의 모든 블록 조회
        cursor = self.conn.execute("""
            SELECT b.content
            FROM blocks b
            JOIN sections s ON b.section_id = s.id
            JOIN documents d ON s.document_id = d.id
            WHERE d.filename LIKE ?
            AND (s.path LIKE ? OR s.title LIKE ?)
        """, (f'%{period}%', f'%{roman}.%', f'%{roman}.%'))

        results = []
        seen_metrics = set()

        for row in cursor:
            metrics = self.parser.extract_all_metrics(row['content'])
            for metric in metrics:
                if metric['name'] not in seen_metrics:
                    results.append(metric)
                    seen_metrics.add(metric['name'])

        return results

    def search_metric_in_db(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        키워드로 지표 검색 (FTS5 활용)

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            검색 결과 목록
        """
        try:
            cursor = self.conn.execute("""
                SELECT b.content, d.filename, s.title
                FROM blocks b
                JOIN blocks_fts ON b.id = blocks_fts.rowid
                JOIN sections s ON b.section_id = s.id
                JOIN documents d ON s.document_id = d.id
                WHERE blocks_fts MATCH ?
                LIMIT ?
            """, (keyword, limit))

            results = []
            for row in cursor:
                period = extract_period_from_filename(row['filename'])
                results.append({
                    'period': period,
                    'section': row['title'],
                    'content': row['content'][:200] + '...' if len(row['content']) > 200 else row['content']
                })
            return results

        except sqlite3.OperationalError:
            # FTS 테이블이 없는 경우 일반 LIKE 검색
            cursor = self.conn.execute("""
                SELECT b.content, d.filename, s.title
                FROM blocks b
                JOIN sections s ON b.section_id = s.id
                JOIN documents d ON s.document_id = d.id
                WHERE b.content LIKE ?
                LIMIT ?
            """, (f'%{keyword}%', limit))

            results = []
            for row in cursor:
                period = extract_period_from_filename(row['filename'])
                results.append({
                    'period': period,
                    'section': row['title'],
                    'content': row['content'][:200] + '...' if len(row['content']) > 200 else row['content']
                })
            return results

    def get_db_stats(self) -> Dict[str, Any]:
        """
        DB 통계 정보 조회

        Returns:
            {
                'documents': int,
                'sections': int,
                'blocks': int,
                'periods': List[str]
            }
        """
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM documents")
        stats['documents'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM sections")
        stats['sections'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM blocks")
        stats['blocks'] = cursor.fetchone()[0]

        stats['periods'] = self.get_available_periods()

        return stats


def main():
    """CLI 인터페이스"""
    import argparse

    parser = argparse.ArgumentParser(
        description='IBK textBook DB 분석 도구'
    )
    parser.add_argument(
        'db_path',
        help='SQLite DB 파일 경로'
    )
    parser.add_argument(
        '--metric', '-m',
        help='조회할 지표명 (예: ROA, 당기순이익)'
    )
    parser.add_argument(
        '--periods', '-p',
        nargs='+',
        help='조회할 기간 목록 (예: 202403 202406)'
    )
    parser.add_argument(
        '--compare', '-c',
        nargs=2,
        metavar=('PERIOD1', 'PERIOD2'),
        help='두 기간 비교 (예: 202410 202510)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='DB 통계 출력'
    )
    parser.add_argument(
        '--search', '-s',
        help='키워드 검색'
    )

    args = parser.parse_args()

    try:
        with TextbookDBAnalyzer(args.db_path) as analyzer:
            if args.stats:
                stats = analyzer.get_db_stats()
                print("=== DB 통계 ===")
                print(f"문서 수: {stats['documents']}")
                print(f"섹션 수: {stats['sections']}")
                print(f"블록 수: {stats['blocks']}")
                print(f"기간: {', '.join(stats['periods'])}")

            elif args.search:
                results = analyzer.search_metric_in_db(args.search)
                print(f"=== '{args.search}' 검색 결과 ===")
                for r in results:
                    print(f"[{r['period']}] {r['section']}")
                    print(f"  {r['content']}")
                    print()

            elif args.metric and args.compare:
                result = analyzer.compare_periods(
                    args.metric,
                    args.compare[0],
                    args.compare[1]
                )
                print(f"=== {args.metric} 비교 분석 ===")
                if result.get('error'):
                    print(f"오류: {result['error']}")
                else:
                    print(f"이전 ({result['prev']['period']}): {result['prev']['value']}{result['prev']['unit']}")
                    print(f"현재 ({result['current']['period']}): {result['current']['value']}{result['current']['unit']}")
                    print(f"변동: {result['change']} ({result['change_pct']:+.2f}%)")

            elif args.metric:
                result = analyzer.get_metric_trend(args.metric, args.periods)
                print(f"=== {args.metric} 추이 ===")
                for label, value in zip(result['labels'], result['values']):
                    print(f"{label}: {value}{result['units']}")

            else:
                # 기본: 통계 출력
                stats = analyzer.get_db_stats()
                print("=== DB 통계 ===")
                print(f"문서 수: {stats['documents']}")
                print(f"섹션 수: {stats['sections']}")
                print(f"블록 수: {stats['blocks']}")
                print(f"기간: {', '.join(stats['periods'])}")

    except FileNotFoundError as e:
        print(f"오류: {e}")
        return 1
    except Exception as e:
        print(f"오류: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
