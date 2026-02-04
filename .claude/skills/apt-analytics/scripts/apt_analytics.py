# -*- coding: utf-8 -*-
"""
아파트 고급 분석 지표 산출
apt.db 데이터를 기반으로 전세가율, 가격변동률, 면적대별/가격대별 통계 등 산출

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

# 면적 구간 정의
AREA_RANGES = [
    ('초소형', 0, 40),
    ('소형', 40, 60),
    ('중소형', 60, 85),
    ('중대형', 85, 135),
    ('대형', 135, 9999)
]

# 가격 구간 정의 (만원)
PRICE_RANGES = [
    ('~3억', 0, 30000),
    ('3~6억', 30000, 60000),
    ('6~10억', 60000, 100000),
    ('10~20억', 100000, 200000),
    ('20~30억', 200000, 300000),
    ('30억~', 300000, 999999999)
]


class AptAnalytics:
    """아파트 분석 지표 산출 클래스"""

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

    def connect(self) -> sqlite3.Connection:
        """DB 연결"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _parse_ym(self, ym: str) -> Tuple[int, int]:
        """년월 파싱"""
        year = int(ym[:4])
        month = int(ym[4:6])
        return year, month

    def _get_prev_month(self, year: int, month: int) -> Tuple[int, int]:
        """전월 계산"""
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def _get_prev_quarter(self, year: int, month: int) -> Tuple[int, int, int, int]:
        """전분기 시작/종료 월 계산"""
        # 현재 분기
        curr_q = (month - 1) // 3 + 1
        if curr_q == 1:
            prev_q_start = (year - 1, 10)
            prev_q_end = (year - 1, 12)
        else:
            prev_q_start_month = (curr_q - 2) * 3 + 1
            prev_q_end_month = (curr_q - 1) * 3
            prev_q_start = (year, prev_q_start_month)
            prev_q_end = (year, prev_q_end_month)
        return prev_q_start[0], prev_q_start[1], prev_q_end[0], prev_q_end[1]

    def _get_region_name(self, sgg_cd: str) -> str:
        """지역코드 → 지역명 조회"""
        # api-apt 메타DB에서 조회
        meta_db_path = PROJECT_ROOT / '.claude' / 'skills' / 'api-apt' / 'data' / 'apt_meta.db'
        if meta_db_path.exists():
            conn = sqlite3.connect(str(meta_db_path))
            cursor = conn.execute(
                "SELECT region_nm, sido_nm FROM region_codes WHERE region_cd = ?",
                (sgg_cd,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"{row[1]} {row[0]}"
        return sgg_cd

    # ==================== 전세가율 ====================

    def calc_jeonse_ratio(self, sgg_cd: str, deal_ym: str) -> Dict[str, Any]:
        """전세가율 산출"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 매매 평균가
        cursor = conn.execute('''
            SELECT AVG(deal_amount_num) as avg_price,
                   COUNT(*) as trade_count
            FROM apt_trades
            WHERE sgg_cd = ?
              AND deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
        ''', (sgg_cd, year, month))
        trade_row = cursor.fetchone()
        avg_trade_price = trade_row['avg_price'] or 0
        trade_count = trade_row['trade_count'] or 0

        # 전세 평균 보증금 (월세 제외)
        cursor = conn.execute('''
            SELECT AVG(deposit) as avg_deposit,
                   COUNT(*) as rent_count
            FROM apt_rents
            WHERE sgg_cd = ?
              AND deal_year = ? AND deal_month = ?
              AND deposit > 0
              AND (monthly_rent IS NULL OR monthly_rent = 0)
        ''', (sgg_cd, year, month))
        rent_row = cursor.fetchone()
        avg_jeonse = rent_row['avg_deposit'] or 0
        jeonse_count = rent_row['rent_count'] or 0

        # 전세가율 계산
        jeonse_ratio = (avg_jeonse / avg_trade_price * 100) if avg_trade_price > 0 else 0

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'deal_ym': deal_ym,
            'avg_trade_price': round(avg_trade_price),
            'trade_count': trade_count,
            'avg_jeonse': round(avg_jeonse),
            'jeonse_count': jeonse_count,
            'jeonse_ratio': round(jeonse_ratio, 1)
        }

    def calc_jeonse_ratio_by_area(self, sgg_cd: str, deal_ym: str) -> List[Dict]:
        """면적별 전세가율 산출"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)
        results = []

        for area_name, min_area, max_area in AREA_RANGES:
            # 매매
            cursor = conn.execute('''
                SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
                  AND exclu_use_ar >= ? AND exclu_use_ar < ?
            ''', (sgg_cd, year, month, min_area, max_area))
            trade = cursor.fetchone()

            # 전세
            cursor = conn.execute('''
                SELECT AVG(deposit) as avg_deposit, COUNT(*) as cnt
                FROM apt_rents
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deposit > 0
                  AND (monthly_rent IS NULL OR monthly_rent = 0)
                  AND exclu_use_ar >= ? AND exclu_use_ar < ?
            ''', (sgg_cd, year, month, min_area, max_area))
            rent = cursor.fetchone()

            avg_trade = trade['avg_price'] or 0
            avg_jeonse = rent['avg_deposit'] or 0
            ratio = (avg_jeonse / avg_trade * 100) if avg_trade > 0 else 0

            results.append({
                'area_type': area_name,
                'min_area': min_area,
                'max_area': max_area,
                'avg_trade_price': round(avg_trade),
                'trade_count': trade['cnt'] or 0,
                'avg_jeonse': round(avg_jeonse),
                'jeonse_count': rent['cnt'] or 0,
                'jeonse_ratio': round(ratio, 1)
            })

        return results

    # ==================== 가격변동률 ====================

    def calc_price_change(self, sgg_cd: str, deal_ym: str, period: str = 'mom') -> Dict[str, Any]:
        """가격변동률 산출 (MoM/QoQ/YoY)"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 현재 기간 평균가
        cursor = conn.execute('''
            SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
            FROM apt_trades
            WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
        ''', (sgg_cd, year, month))
        curr = cursor.fetchone()
        curr_price = curr['avg_price'] or 0
        curr_count = curr['cnt'] or 0

        # 비교 기간
        if period == 'mom':
            prev_year, prev_month = self._get_prev_month(year, month)
            cursor = conn.execute('''
                SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
            ''', (sgg_cd, prev_year, prev_month))
            prev = cursor.fetchone()
            prev_price = prev['avg_price'] or 0
            prev_count = prev['cnt'] or 0
            compare_period = f"{prev_year}년 {prev_month}월"

        elif period == 'yoy':
            prev_year = year - 1
            cursor = conn.execute('''
                SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
            ''', (sgg_cd, prev_year, month))
            prev = cursor.fetchone()
            prev_price = prev['avg_price'] or 0
            prev_count = prev['cnt'] or 0
            compare_period = f"{prev_year}년 {month}월"

        elif period == 'qoq':
            # 현재 분기 평균
            curr_q = (month - 1) // 3 + 1
            curr_q_start = (curr_q - 1) * 3 + 1
            curr_q_end = curr_q * 3

            cursor = conn.execute('''
                SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ?
                  AND deal_month >= ? AND deal_month <= ?
                  AND deal_amount_num > 0
            ''', (sgg_cd, year, curr_q_start, curr_q_end))
            curr_q_data = cursor.fetchone()
            curr_price = curr_q_data['avg_price'] or 0
            curr_count = curr_q_data['cnt'] or 0

            # 전분기 평균
            py1, pm1, py2, pm2 = self._get_prev_quarter(year, month)
            if py1 == py2:
                cursor = conn.execute('''
                    SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                    FROM apt_trades
                    WHERE sgg_cd = ? AND deal_year = ?
                      AND deal_month >= ? AND deal_month <= ?
                      AND deal_amount_num > 0
                ''', (sgg_cd, py1, pm1, pm2))
            else:
                cursor = conn.execute('''
                    SELECT AVG(deal_amount_num) as avg_price, COUNT(*) as cnt
                    FROM apt_trades
                    WHERE sgg_cd = ?
                      AND ((deal_year = ? AND deal_month >= ?)
                           OR (deal_year = ? AND deal_month <= ?))
                      AND deal_amount_num > 0
                ''', (sgg_cd, py1, pm1, py2, pm2))
            prev = cursor.fetchone()
            prev_price = prev['avg_price'] or 0
            prev_count = prev['cnt'] or 0
            compare_period = f"{py1}년 Q{(pm1-1)//3+1}"

        else:
            raise ValueError(f"Unknown period: {period}")

        # 변동률 계산
        if prev_price > 0:
            change_rate = (curr_price - prev_price) / prev_price * 100
            change_amount = curr_price - prev_price
        else:
            change_rate = 0
            change_amount = 0

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'deal_ym': deal_ym,
            'period_type': period.upper(),
            'curr_price': round(curr_price),
            'curr_count': curr_count,
            'prev_price': round(prev_price),
            'prev_count': prev_count,
            'compare_period': compare_period,
            'change_rate': round(change_rate, 2),
            'change_amount': round(change_amount)
        }

    # ==================== 면적대별 통계 ====================

    def calc_by_area(self, sgg_cd: str, deal_ym: str) -> List[Dict]:
        """면적대별 거래 통계"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 전체 건수
        cursor = conn.execute('''
            SELECT COUNT(*) as total
            FROM apt_trades
            WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
        ''', (sgg_cd, year, month))
        total_count = cursor.fetchone()['total'] or 1

        results = []
        for area_name, min_area, max_area in AREA_RANGES:
            cursor = conn.execute('''
                SELECT COUNT(*) as cnt,
                       AVG(deal_amount_num) as avg_price,
                       MIN(deal_amount_num) as min_price,
                       MAX(deal_amount_num) as max_price,
                       AVG(deal_amount_num / exclu_use_ar) as avg_unit_price
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num > 0
                  AND exclu_use_ar >= ? AND exclu_use_ar < ?
            ''', (sgg_cd, year, month, min_area, max_area))
            row = cursor.fetchone()

            cnt = row['cnt'] or 0
            ratio = (cnt / total_count * 100) if total_count > 0 else 0

            results.append({
                'area_type': area_name,
                'area_range': f"{min_area}~{max_area if max_area < 9999 else ''}㎡",
                'count': cnt,
                'ratio': round(ratio, 1),
                'avg_price': round(row['avg_price'] or 0),
                'min_price': round(row['min_price'] or 0),
                'max_price': round(row['max_price'] or 0),
                'avg_unit_price': round(row['avg_unit_price'] or 0)
            })

        return results

    # ==================== 가격대별 분포 ====================

    def calc_by_price(self, sgg_cd: str, deal_ym: str) -> List[Dict]:
        """가격대별 거래 분포"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 전체 건수
        cursor = conn.execute('''
            SELECT COUNT(*) as total
            FROM apt_trades
            WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
              AND deal_amount_num > 0
        ''', (sgg_cd, year, month))
        total_count = cursor.fetchone()['total'] or 1

        results = []
        for price_name, min_price, max_price in PRICE_RANGES:
            cursor = conn.execute('''
                SELECT COUNT(*) as cnt,
                       AVG(exclu_use_ar) as avg_area
                FROM apt_trades
                WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                  AND deal_amount_num >= ? AND deal_amount_num < ?
            ''', (sgg_cd, year, month, min_price, max_price))
            row = cursor.fetchone()

            cnt = row['cnt'] or 0
            ratio = (cnt / total_count * 100) if total_count > 0 else 0

            results.append({
                'price_range': price_name,
                'count': cnt,
                'ratio': round(ratio, 1),
                'avg_area': round(row['avg_area'] or 0, 1)
            })

        return results

    # ==================== 시장과열지수 ====================

    def calc_overheat_index(self, sgg_cd: str, deal_ym: str) -> Dict[str, Any]:
        """시장과열지수 산출 (0~100)"""
        conn = self.connect()
        year, month = self._parse_ym(deal_ym)

        # 1. 거래량 점수 (30점) - 전년 동월 대비
        cursor = conn.execute('''
            SELECT COUNT(*) as cnt FROM apt_trades
            WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
        ''', (sgg_cd, year, month))
        curr_volume = cursor.fetchone()['cnt'] or 0

        cursor = conn.execute('''
            SELECT COUNT(*) as cnt FROM apt_trades
            WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
        ''', (sgg_cd, year - 1, month))
        prev_volume = cursor.fetchone()['cnt'] or 1

        volume_change = (curr_volume - prev_volume) / prev_volume * 100 if prev_volume > 0 else 0
        # -50% 이하: 0점, +100% 이상: 30점
        volume_score = min(30, max(0, (volume_change + 50) / 150 * 30))

        # 2. 가격상승률 점수 (40점) - 전년 동월 대비
        price_change = self.calc_price_change(sgg_cd, deal_ym, 'yoy')
        price_change_rate = price_change['change_rate']
        # -10% 이하: 0점, +20% 이상: 40점
        price_score = min(40, max(0, (price_change_rate + 10) / 30 * 40))

        # 3. 전세가율 점수 (30점)
        jeonse = self.calc_jeonse_ratio(sgg_cd, deal_ym)
        jeonse_ratio = jeonse['jeonse_ratio']
        # 50% 이하: 0점, 90% 이상: 30점
        jeonse_score = min(30, max(0, (jeonse_ratio - 50) / 40 * 30))

        # 종합 점수
        total_score = round(volume_score + price_score + jeonse_score, 1)

        # 등급 판정
        if total_score < 30:
            grade = '침체'
        elif total_score < 50:
            grade = '안정'
        elif total_score < 70:
            grade = '활황'
        else:
            grade = '과열'

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'deal_ym': deal_ym,
            'volume_score': round(volume_score, 1),
            'volume_change': round(volume_change, 1),
            'price_score': round(price_score, 1),
            'price_change': round(price_change_rate, 1),
            'jeonse_score': round(jeonse_score, 1),
            'jeonse_ratio': jeonse_ratio,
            'total_score': total_score,
            'grade': grade
        }

    # ==================== 종합 분석 ====================

    def full_analysis(self, sgg_cd: str, deal_ym: str) -> Dict[str, Any]:
        """종합 분석 (모든 지표)"""
        return {
            'jeonse_ratio': self.calc_jeonse_ratio(sgg_cd, deal_ym),
            'jeonse_by_area': self.calc_jeonse_ratio_by_area(sgg_cd, deal_ym),
            'price_change_mom': self.calc_price_change(sgg_cd, deal_ym, 'mom'),
            'price_change_yoy': self.calc_price_change(sgg_cd, deal_ym, 'yoy'),
            'by_area': self.calc_by_area(sgg_cd, deal_ym),
            'by_price': self.calc_by_price(sgg_cd, deal_ym),
            'overheat_index': self.calc_overheat_index(sgg_cd, deal_ym)
        }


# ==================== 출력 포맷터 ====================

def format_jeonse_ratio(data: Dict, by_area: List[Dict] = None) -> str:
    """전세가율 마크다운 포맷"""
    lines = [
        f"## 전세가율 분석 ({data['region_name']}, {data['deal_ym'][:4]}.{data['deal_ym'][4:]})",
        "",
        f"| 구분 | 매매 평균가 | 전세 평균가 | 전세가율 |",
        f"|------|------------|------------|----------|",
        f"| 전체 | {data['avg_trade_price']:,}만원 | {data['avg_jeonse']:,}만원 | {data['jeonse_ratio']}% |"
    ]

    if by_area:
        for row in by_area:
            if row['trade_count'] > 0 or row['jeonse_count'] > 0:
                lines.append(
                    f"| {row['area_type']} ({row['min_area']}~{row['max_area'] if row['max_area'] < 9999 else ''}㎡) "
                    f"| {row['avg_trade_price']:,}만원 | {row['avg_jeonse']:,}만원 | {row['jeonse_ratio']}% |"
                )

    lines.extend([
        "",
        f"**거래건수**: 매매 {data['trade_count']}건, 전세 {data['jeonse_count']}건"
    ])

    return "\n".join(lines)


def format_price_change(data: Dict) -> str:
    """가격변동률 마크다운 포맷"""
    sign = '+' if data['change_rate'] >= 0 else ''
    return "\n".join([
        f"## 가격변동률 ({data['region_name']}, {data['period_type']})",
        "",
        f"| 기준월 | 비교기간 | 현재 평균가 | 이전 평균가 | 변동률 | 변동액 |",
        f"|--------|----------|------------|------------|--------|--------|",
        f"| {data['deal_ym'][:4]}.{data['deal_ym'][4:]} | {data['compare_period']} "
        f"| {data['curr_price']:,}만원 | {data['prev_price']:,}만원 "
        f"| {sign}{data['change_rate']}% | {sign}{data['change_amount']:,}만원 |",
        "",
        f"**거래건수**: 현재 {data['curr_count']}건, 이전 {data['prev_count']}건"
    ])


def format_by_area(data: List[Dict], region_name: str, deal_ym: str) -> str:
    """면적대별 통계 마크다운 포맷"""
    lines = [
        f"## 면적대별 거래 현황 ({region_name}, {deal_ym[:4]}.{deal_ym[4:]})",
        "",
        "| 면적 구간 | 건수 | 비중 | 평균가 | 최저가 | 최고가 | 평단가(만원/㎡) |",
        "|-----------|------|------|--------|--------|--------|-----------------|"
    ]

    for row in data:
        lines.append(
            f"| {row['area_type']} ({row['area_range']}) | {row['count']}건 | {row['ratio']}% "
            f"| {row['avg_price']:,} | {row['min_price']:,} | {row['max_price']:,} "
            f"| {row['avg_unit_price']:,} |"
        )

    return "\n".join(lines)


def format_by_price(data: List[Dict], region_name: str, deal_ym: str) -> str:
    """가격대별 분포 마크다운 포맷"""
    lines = [
        f"## 가격대별 거래 분포 ({region_name}, {deal_ym[:4]}.{deal_ym[4:]})",
        "",
        "| 가격 구간 | 건수 | 비중 | 평균 면적 |",
        "|-----------|------|------|----------|"
    ]

    for row in data:
        lines.append(
            f"| {row['price_range']} | {row['count']}건 | {row['ratio']}% | {row['avg_area']}㎡ |"
        )

    return "\n".join(lines)


def format_overheat_index(data: Dict) -> str:
    """시장과열지수 마크다운 포맷"""
    return "\n".join([
        f"## 시장과열지수 ({data['region_name']}, {data['deal_ym'][:4]}.{data['deal_ym'][4:]})",
        "",
        f"### 종합 점수: {data['total_score']}점 ({data['grade']})",
        "",
        "| 구성 요소 | 점수 | 세부 지표 |",
        "|-----------|------|-----------|",
        f"| 거래량 변화 | {data['volume_score']}/30 | 전년 동월 대비 {data['volume_change']:+.1f}% |",
        f"| 가격 상승률 | {data['price_score']}/40 | 전년 동월 대비 {data['price_change']:+.1f}% |",
        f"| 전세가율 | {data['jeonse_score']}/30 | {data['jeonse_ratio']}% |",
        "",
        "**등급 기준**: 침체(~30) / 안정(30~50) / 활황(50~70) / 과열(70~)"
    ])


def format_full_analysis(data: Dict) -> str:
    """종합 분석 마크다운 포맷"""
    jeonse = data['jeonse_ratio']
    region_name = jeonse['region_name']
    deal_ym = jeonse['deal_ym']

    parts = [
        f"# 아파트 시장 종합 분석: {region_name}",
        f"**분석 기준월**: {deal_ym[:4]}년 {deal_ym[4:]}월",
        "",
        "---",
        "",
        format_jeonse_ratio(data['jeonse_ratio'], data['jeonse_by_area']),
        "",
        "---",
        "",
        format_price_change(data['price_change_mom']),
        "",
        format_price_change(data['price_change_yoy']),
        "",
        "---",
        "",
        format_by_area(data['by_area'], region_name, deal_ym),
        "",
        "---",
        "",
        format_by_price(data['by_price'], region_name, deal_ym),
        "",
        "---",
        "",
        format_overheat_index(data['overheat_index'])
    ]

    return "\n".join(parts)


# ==================== CLI ====================

def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='아파트 고급 분석 지표 산출',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 명령
    parser.add_argument('--jeonse-ratio', action='store_true', help='전세가율 산출')
    parser.add_argument('--price-change', action='store_true', help='가격변동률 산출')
    parser.add_argument('--by-area', action='store_true', help='면적대별 통계')
    parser.add_argument('--by-price', action='store_true', help='가격대별 분포')
    parser.add_argument('--overheat-index', action='store_true', help='시장과열지수')
    parser.add_argument('--full', action='store_true', help='종합 분석')

    # 옵션
    parser.add_argument('--region', '-r', type=str, required=True, help='지역코드 (쉼표 구분 복수 가능)')
    parser.add_argument('--ym', type=str, help='분석 년월 (YYYYMM)')
    parser.add_argument('--period', type=str, default='mom', help='비교 기간 (mom/qoq/yoy)')
    parser.add_argument('--output', '-o', type=str, help='결과 저장 파일')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    # 기본값
    if not args.ym:
        now = datetime.now()
        args.ym = now.strftime('%Y%m')

    analytics = AptAnalytics(args.db)

    try:
        regions = [r.strip() for r in args.region.split(',')]
        output_lines = []

        for sgg_cd in regions:
            if args.jeonse_ratio:
                data = analytics.calc_jeonse_ratio(sgg_cd, args.ym)
                by_area = analytics.calc_jeonse_ratio_by_area(sgg_cd, args.ym)
                output_lines.append(format_jeonse_ratio(data, by_area))

            elif args.price_change:
                data = analytics.calc_price_change(sgg_cd, args.ym, args.period)
                output_lines.append(format_price_change(data))

            elif args.by_area:
                data = analytics.calc_by_area(sgg_cd, args.ym)
                region_name = analytics._get_region_name(sgg_cd)
                output_lines.append(format_by_area(data, region_name, args.ym))

            elif args.by_price:
                data = analytics.calc_by_price(sgg_cd, args.ym)
                region_name = analytics._get_region_name(sgg_cd)
                output_lines.append(format_by_price(data, region_name, args.ym))

            elif args.overheat_index:
                data = analytics.calc_overheat_index(sgg_cd, args.ym)
                output_lines.append(format_overheat_index(data))

            elif args.full:
                data = analytics.full_analysis(sgg_cd, args.ym)
                output_lines.append(format_full_analysis(data))

            else:
                parser.print_help()
                return

            output_lines.append("")

        output = "\n".join(output_lines)
        print(output)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n[저장됨] {args.output}")

    finally:
        analytics.close()


if __name__ == '__main__':
    main()
