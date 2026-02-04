# -*- coding: utf-8 -*-
"""
아파트 지역 비교 분석
apt.db 데이터를 기반으로 지역 랭킹, 지역 비교, 시도별 집계 등 분석

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
APT_DB_PATH = PROJECT_ROOT / '3_Resources' / 'R-DB' / 'apt.db'
META_DB_PATH = PROJECT_ROOT / '.claude' / 'skills' / 'api-apt' / 'data' / 'apt_meta.db'


class AptRegion:
    """아파트 지역 비교 분석 클래스"""

    def __init__(self, db_path: Optional[str] = None):
        """초기화"""
        if db_path is None:
            db_path = str(APT_DB_PATH)

        if not Path(db_path).exists():
            print(f"[ERROR] apt.db 파일을 찾을 수 없습니다: {db_path}")
            print("api-apt 스킬로 데이터를 먼저 동기화하세요.")
            sys.exit(1)

        self.db_path = db_path
        self.conn = None
        self.meta_conn = None
        self._region_cache = {}

    def connect(self) -> sqlite3.Connection:
        """DB 연결"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def connect_meta(self) -> Optional[sqlite3.Connection]:
        """메타DB 연결"""
        if self.meta_conn is None and META_DB_PATH.exists():
            self.meta_conn = sqlite3.connect(str(META_DB_PATH))
            self.meta_conn.row_factory = sqlite3.Row
        return self.meta_conn

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.meta_conn:
            self.meta_conn.close()
            self.meta_conn = None

    def _get_region_info(self, sgg_cd: str) -> Dict[str, str]:
        """지역코드 → 지역 정보"""
        if sgg_cd in self._region_cache:
            return self._region_cache[sgg_cd]

        info = {'region_cd': sgg_cd, 'region_nm': sgg_cd, 'sido_nm': ''}

        meta = self.connect_meta()
        if meta:
            cursor = meta.execute(
                "SELECT region_nm, sido_nm FROM region_codes WHERE region_cd = ?",
                (sgg_cd,)
            )
            row = cursor.fetchone()
            if row:
                info = {
                    'region_cd': sgg_cd,
                    'region_nm': row['region_nm'],
                    'sido_nm': row['sido_nm']
                }

        self._region_cache[sgg_cd] = info
        return info

    def _get_sido_regions(self, sgg_cd: str) -> List[str]:
        """같은 시도 내 지역코드 목록"""
        info = self._get_region_info(sgg_cd)
        sido_nm = info.get('sido_nm', '')

        meta = self.connect_meta()
        if not meta or not sido_nm:
            return [sgg_cd]

        cursor = meta.execute(
            "SELECT region_cd FROM region_codes WHERE sido_nm = ?",
            (sido_nm,)
        )
        return [row['region_cd'] for row in cursor.fetchall()]

    def _parse_ym(self, ym: str) -> Tuple[int, int]:
        """년월 파싱"""
        return int(ym[:4]), int(ym[4:6])

    # ==================== 지역 랭킹 ====================

    def get_ranking(self, deal_ym: str, top_n: int = 20, by: str = 'price') -> List[Dict]:
        """지역 랭킹 조회"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        order_col = 'avg_price' if by == 'price' else 'volume'

        cursor = conn.execute(f'''
            SELECT
                sgg_cd,
                COUNT(*) as volume,
                AVG(deal_amount_num) as avg_price,
                AVG(deal_amount_num / exclu_use_ar) as avg_unit_price,
                MIN(deal_amount_num) as min_price,
                MAX(deal_amount_num) as max_price
            FROM apt_trades
            WHERE deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
            GROUP BY sgg_cd
            HAVING COUNT(*) >= 5
            ORDER BY {order_col} DESC
            LIMIT ?
        ''', (year, month, top_n))

        results = []
        for i, row in enumerate(cursor.fetchall(), 1):
            info = self._get_region_info(row['sgg_cd'])
            results.append({
                'rank': i,
                'region_cd': row['sgg_cd'],
                'region_nm': info['region_nm'],
                'sido_nm': info['sido_nm'],
                'volume': row['volume'],
                'avg_price': round(row['avg_price']),
                'avg_unit_price': round(row['avg_unit_price']),
                'min_price': round(row['min_price']),
                'max_price': round(row['max_price'])
            })

        return results

    # ==================== 지역 비교 ====================

    def compare_regions(self, sgg_codes: List[str], deal_ym: str) -> List[Dict]:
        """복수 지역 비교"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)
        prev_year = year - 1  # YoY 비교용

        results = []
        for sgg_cd in sgg_codes:
            # 현재 데이터
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as volume,
                    AVG(deal_amount_num) as avg_price,
                    AVG(deal_amount_num / exclu_use_ar) as avg_unit_price
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
            ''', (sgg_cd, year, month))
            curr = cursor.fetchone()

            # 전년 동월 데이터
            cursor = conn.execute('''
                SELECT AVG(deal_amount_num) as avg_price
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
            ''', (sgg_cd, prev_year, month))
            prev = cursor.fetchone()

            # 전세가율 계산
            cursor = conn.execute('''
                SELECT AVG(deposit) as avg_jeonse
                FROM apt_rents
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deposit > 0
                  AND (monthly_rent IS NULL OR monthly_rent = 0)
            ''', (sgg_cd, year, month))
            jeonse = cursor.fetchone()

            curr_price = curr['avg_price'] or 0
            prev_price = prev['avg_price'] or 0
            jeonse_price = jeonse['avg_jeonse'] or 0

            yoy_change = ((curr_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
            jeonse_ratio = (jeonse_price / curr_price * 100) if curr_price > 0 else 0

            info = self._get_region_info(sgg_cd)
            results.append({
                'region_cd': sgg_cd,
                'region_nm': info['region_nm'],
                'sido_nm': info['sido_nm'],
                'volume': curr['volume'] or 0,
                'avg_price': round(curr_price),
                'avg_unit_price': round(curr['avg_unit_price'] or 0),
                'jeonse_ratio': round(jeonse_ratio, 1),
                'yoy_change': round(yoy_change, 1)
            })

        # 가격순 정렬
        results.sort(key=lambda x: x['avg_price'], reverse=True)
        return results

    # ==================== 인접 지역 비교 ====================

    def compare_adjacent(self, sgg_cd: str, deal_ym: str) -> Dict[str, Any]:
        """같은 시도 내 인접 지역 비교"""
        adjacent_codes = self._get_sido_regions(sgg_cd)
        info = self._get_region_info(sgg_cd)

        results = self.compare_regions(adjacent_codes, deal_ym)

        # 기준 지역 순위 찾기
        base_rank = None
        for i, r in enumerate(results, 1):
            if r['region_cd'] == sgg_cd:
                base_rank = i
                break

        return {
            'base_region': info['region_nm'],
            'sido': info['sido_nm'],
            'base_rank': base_rank,
            'total_regions': len(results),
            'deal_ym': deal_ym,
            'regions': results
        }

    # ==================== 시도별 집계 ====================

    def aggregate_by_sido(self, deal_ym: str) -> List[Dict]:
        """시도별 평균 통계"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 지역별 데이터
        cursor = conn.execute('''
            SELECT
                sgg_cd,
                COUNT(*) as volume,
                AVG(deal_amount_num) as avg_price
            FROM apt_trades
            WHERE deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
            GROUP BY sgg_cd
        ''', (year, month))

        # 시도별 집계
        sido_data = {}
        for row in cursor.fetchall():
            info = self._get_region_info(row['sgg_cd'])
            sido = info['sido_nm'] or '기타'

            if sido not in sido_data:
                sido_data[sido] = {
                    'total_volume': 0,
                    'total_value': 0,
                    'region_count': 0
                }

            sido_data[sido]['total_volume'] += row['volume']
            sido_data[sido]['total_value'] += row['avg_price'] * row['volume']
            sido_data[sido]['region_count'] += 1

        # 결과 정리
        results = []
        for sido, data in sido_data.items():
            avg_price = data['total_value'] / data['total_volume'] if data['total_volume'] > 0 else 0
            results.append({
                'sido': sido,
                'region_count': data['region_count'],
                'total_volume': data['total_volume'],
                'avg_price': round(avg_price)
            })

        # 평균가순 정렬
        results.sort(key=lambda x: x['avg_price'], reverse=True)
        return results

    # ==================== 가격 격차 분석 ====================

    def analyze_gap(self, sgg_code1: str, sgg_code2: str, deal_ym: str) -> Dict[str, Any]:
        """두 지역 간 가격 격차 분석"""
        comparison = self.compare_regions([sgg_code1, sgg_code2], deal_ym)

        if len(comparison) < 2:
            return {'error': '데이터 부족'}

        r1, r2 = comparison[0], comparison[1]

        gap_amount = r1['avg_price'] - r2['avg_price']
        gap_ratio = (gap_amount / r2['avg_price'] * 100) if r2['avg_price'] > 0 else 0

        return {
            'deal_ym': deal_ym,
            'region_high': r1,
            'region_low': r2,
            'gap_amount': gap_amount,
            'gap_ratio': round(gap_ratio, 1)
        }

    # ==================== 종합 분석 ====================

    def full_analysis(self, deal_ym: str) -> Dict[str, Any]:
        """종합 분석"""
        return {
            'ranking_price': self.get_ranking(deal_ym, 20, 'price'),
            'ranking_volume': self.get_ranking(deal_ym, 10, 'volume'),
            'sido_summary': self.aggregate_by_sido(deal_ym)
        }


# ==================== 출력 포맷터 ====================

def format_ranking(data: List[Dict], ym: str, by: str = 'price') -> str:
    """랭킹 마크다운 포맷"""
    title = '평균가' if by == 'price' else '거래량'
    lines = [
        f"## 지역 랭킹 ({title} 기준, {ym[:4]}.{ym[4:]})",
        "",
        "| 순위 | 지역 | 시도 | 평균가 | 거래량 | 평단가(만/㎡) |",
        "|------|------|------|--------|--------|---------------|"
    ]

    for r in data:
        lines.append(
            f"| {r['rank']} | {r['region_nm']} | {r['sido_nm']} "
            f"| {r['avg_price']:,}만원 | {r['volume']}건 | {r['avg_unit_price']:,} |"
        )

    return "\n".join(lines)


def format_compare(data: List[Dict], ym: str) -> str:
    """비교 마크다운 포맷"""
    lines = [
        f"## 지역 비교 분석 ({ym[:4]}.{ym[4:]})",
        "",
        "| 지역 | 시도 | 평균가 | 거래량 | 전세가율 | YoY변동 |",
        "|------|------|--------|--------|----------|---------|"
    ]

    for r in data:
        yoy_sign = '+' if r['yoy_change'] >= 0 else ''
        lines.append(
            f"| {r['region_nm']} | {r['sido_nm']} | {r['avg_price']:,}만원 "
            f"| {r['volume']}건 | {r['jeonse_ratio']}% | {yoy_sign}{r['yoy_change']}% |"
        )

    return "\n".join(lines)


def format_adjacent(data: Dict) -> str:
    """인접 지역 비교 마크다운 포맷"""
    lines = [
        f"## 인접 지역 비교 ({data['sido']}, {data['deal_ym'][:4]}.{data['deal_ym'][4:]})",
        "",
        f"**기준 지역**: {data['base_region']} (전체 {data['total_regions']}개 중 {data['base_rank']}위)",
        "",
        "| 순위 | 지역 | 평균가 | 거래량 | 전세가율 | YoY변동 |",
        "|------|------|--------|--------|----------|---------|"
    ]

    for i, r in enumerate(data['regions'], 1):
        yoy_sign = '+' if r['yoy_change'] >= 0 else ''
        marker = ' *' if r['region_nm'] == data['base_region'] else ''
        lines.append(
            f"| {i} | {r['region_nm']}{marker} | {r['avg_price']:,}만원 "
            f"| {r['volume']}건 | {r['jeonse_ratio']}% | {yoy_sign}{r['yoy_change']}% |"
        )

    return "\n".join(lines)


def format_sido(data: List[Dict], ym: str) -> str:
    """시도별 집계 마크다운 포맷"""
    lines = [
        f"## 시도별 아파트 시장 현황 ({ym[:4]}.{ym[4:]})",
        "",
        "| 시도 | 지역 수 | 총 거래량 | 평균가 |",
        "|------|---------|----------|--------|"
    ]

    for r in data:
        lines.append(
            f"| {r['sido']} | {r['region_count']}개 | {r['total_volume']:,}건 | {r['avg_price']:,}만원 |"
        )

    return "\n".join(lines)


def format_gap(data: Dict) -> str:
    """가격 격차 마크다운 포맷"""
    high = data['region_high']
    low = data['region_low']

    return "\n".join([
        f"## 가격 격차 분석 ({data['deal_ym'][:4]}.{data['deal_ym'][4:]})",
        "",
        "| 항목 | 고가 지역 | 저가 지역 |",
        "|------|----------|----------|",
        f"| 지역명 | {high['region_nm']} | {low['region_nm']} |",
        f"| 시도 | {high['sido_nm']} | {low['sido_nm']} |",
        f"| 평균가 | {high['avg_price']:,}만원 | {low['avg_price']:,}만원 |",
        f"| 거래량 | {high['volume']}건 | {low['volume']}건 |",
        "",
        f"**가격 격차**: {data['gap_amount']:,}만원 ({data['gap_ratio']}%)"
    ])


def format_full(data: Dict, ym: str) -> str:
    """종합 분석 마크다운 포맷"""
    parts = [
        f"# 아파트 지역 비교 분석 종합",
        f"**분석 기준월**: {ym[:4]}년 {ym[4:]}월",
        "",
        "---",
        "",
        format_ranking(data['ranking_price'], ym, 'price'),
        "",
        "---",
        "",
        format_ranking(data['ranking_volume'], ym, 'volume'),
        "",
        "---",
        "",
        format_sido(data['sido_summary'], ym)
    ]

    return "\n".join(parts)


# ==================== CLI ====================

def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='아파트 지역 비교 분석',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 명령
    parser.add_argument('--rank', type=str, help='지역 랭킹 (top10/top20/top30)')
    parser.add_argument('--compare', type=str, help='지역 비교 (쉼표 구분 코드)')
    parser.add_argument('--adjacent', type=str, help='인접 지역 비교 (기준 지역코드)')
    parser.add_argument('--by-sido', action='store_true', help='시도별 집계')
    parser.add_argument('--gap', type=str, help='가격 격차 (두 지역코드 쉼표 구분)')
    parser.add_argument('--full', action='store_true', help='종합 분석')

    # 옵션
    parser.add_argument('--ym', type=str, help='분석 년월 (YYYYMM)')
    parser.add_argument('--by', type=str, default='price', choices=['price', 'volume'], help='정렬 기준')
    parser.add_argument('--output', '-o', type=str, help='결과 저장 파일')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    # 기본값
    if not args.ym:
        now = datetime.now()
        args.ym = now.strftime('%Y%m')

    region = AptRegion(args.db)

    try:
        output = ""

        if args.rank:
            n = int(args.rank.replace('top', ''))
            data = region.get_ranking(args.ym, n, args.by)
            output = format_ranking(data, args.ym, args.by)

        elif args.compare:
            codes = [c.strip() for c in args.compare.split(',')]
            data = region.compare_regions(codes, args.ym)
            output = format_compare(data, args.ym)

        elif args.adjacent:
            data = region.compare_adjacent(args.adjacent, args.ym)
            output = format_adjacent(data)

        elif args.by_sido:
            data = region.aggregate_by_sido(args.ym)
            output = format_sido(data, args.ym)

        elif args.gap:
            codes = [c.strip() for c in args.gap.split(',')]
            if len(codes) != 2:
                print("[ERROR] 두 지역코드를 쉼표로 구분하여 입력하세요")
                return
            data = region.analyze_gap(codes[0], codes[1], args.ym)
            output = format_gap(data)

        elif args.full:
            data = region.full_analysis(args.ym)
            output = format_full(data, args.ym)

        else:
            parser.print_help()
            return

        print(output)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n[저장됨] {args.output}")

    finally:
        region.close()


if __name__ == '__main__':
    main()
