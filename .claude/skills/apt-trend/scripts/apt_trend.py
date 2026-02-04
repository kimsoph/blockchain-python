# -*- coding: utf-8 -*-
"""
아파트 시계열 트렌드 분석
apt.db 데이터를 기반으로 이동평균, 추세선, 변동성, 계절성, 변곡점 분석

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
import math

# 한글 출력 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
APT_DB_PATH = PROJECT_ROOT / '3_Resources' / 'R-DB' / 'apt.db'


class AptTrend:
    """아파트 시계열 트렌드 분석 클래스"""

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

    def _parse_period(self, period: str) -> Tuple[str, str]:
        """기간 파싱 (YYYYMM-YYYYMM)"""
        parts = period.split('-')
        if len(parts) == 2:
            return parts[0], parts[1]
        return period, period

    def _generate_months(self, start_ym: str, end_ym: str) -> List[str]:
        """기간 내 월 목록 생성"""
        months = []
        sy, sm = int(start_ym[:4]), int(start_ym[4:6])
        ey, em = int(end_ym[:4]), int(end_ym[4:6])

        current_y, current_m = sy, sm
        while (current_y < ey) or (current_y == ey and current_m <= em):
            months.append(f"{current_y}{current_m:02d}")
            current_m += 1
            if current_m > 12:
                current_m = 1
                current_y += 1

        return months

    def _get_region_name(self, sgg_cd: str) -> str:
        """지역코드 → 지역명 조회"""
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

    def _get_monthly_data(self, sgg_cd: str, start_ym: str, end_ym: str, metric: str = 'price') -> List[Dict]:
        """월별 데이터 조회"""
        conn = self.connect()
        months = self._generate_months(start_ym, end_ym)

        results = []
        for ym in months:
            year, month = int(ym[:4]), int(ym[4:6])

            if metric == 'price':
                cursor = conn.execute('''
                    SELECT AVG(deal_amount_num) as value, COUNT(*) as volume
                    FROM apt_trades
                    WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                      AND deal_amount_num > 0
                ''', (sgg_cd, year, month))
            else:  # volume
                cursor = conn.execute('''
                    SELECT COUNT(*) as value, AVG(deal_amount_num) as price
                    FROM apt_trades
                    WHERE sgg_cd = ? AND deal_year = ? AND deal_month = ?
                ''', (sgg_cd, year, month))

            row = cursor.fetchone()
            volume_val = row['volume'] if 'volume' in row.keys() else 0
            results.append({
                'ym': ym,
                'year': year,
                'month': month,
                'value': row['value'] or 0,
                'volume': volume_val or 0
            })

        return results

    # ==================== 이동평균 ====================

    def calc_moving_average(self, sgg_cd: str, period: str, windows: List[int] = [3, 6, 12]) -> Dict[str, Any]:
        """이동평균 산출"""
        start_ym, end_ym = self._parse_period(period)
        data = self._get_monthly_data(sgg_cd, start_ym, end_ym)

        if len(data) < max(windows):
            print(f"[WARNING] 데이터 부족: {len(data)}개월 (최소 {max(windows)}개월 필요)")

        # 이동평균 계산
        for row in data:
            idx = data.index(row)
            for w in windows:
                if idx >= w - 1:
                    values = [data[i]['value'] for i in range(idx - w + 1, idx + 1)]
                    row[f'ma{w}'] = round(sum(values) / w) if values else 0
                else:
                    row[f'ma{w}'] = None

        # 신호 판정 (골든/데드 크로스)
        if len(windows) >= 2:
            short_w, long_w = min(windows), max(windows)
            for i, row in enumerate(data):
                if i > 0 and row.get(f'ma{short_w}') and row.get(f'ma{long_w}'):
                    prev = data[i - 1]
                    if prev.get(f'ma{short_w}') and prev.get(f'ma{long_w}'):
                        short_curr = row[f'ma{short_w}']
                        long_curr = row[f'ma{long_w}']
                        short_prev = prev[f'ma{short_w}']
                        long_prev = prev[f'ma{long_w}']

                        if short_prev <= long_prev and short_curr > long_curr:
                            row['signal'] = '골든크로스'
                        elif short_prev >= long_prev and short_curr < long_curr:
                            row['signal'] = '데드크로스'
                        elif short_curr > long_curr:
                            row['signal'] = '상승'
                        else:
                            row['signal'] = '하락'

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'period': period,
            'windows': windows,
            'data': data
        }

    # ==================== 추세선 ====================

    def calc_trend(self, sgg_cd: str, period: str, trend_type: str = 'linear') -> Dict[str, Any]:
        """추세선 분석"""
        start_ym, end_ym = self._parse_period(period)
        data = self._get_monthly_data(sgg_cd, start_ym, end_ym)

        n = len(data)
        if n < 3:
            return {'error': '데이터 부족 (최소 3개월 필요)'}

        # X, Y 값
        x = list(range(n))
        y = [d['value'] for d in data]

        # 선형 회귀
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
            intercept = y_mean
        else:
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

        # 예측값 및 R²
        y_pred = [slope * xi + intercept for xi in x]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 월평균 변화율
        if y[0] > 0:
            monthly_change = slope / y[0] * 100
        else:
            monthly_change = 0

        # 추세 방향
        if slope > 0:
            direction = '상승'
        elif slope < 0:
            direction = '하락'
        else:
            direction = '횡보'

        # 예측값 추가
        for i, row in enumerate(data):
            row['trend'] = round(y_pred[i])

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'period': period,
            'trend_type': trend_type,
            'slope': round(slope, 2),
            'intercept': round(intercept),
            'r_squared': round(r_squared, 3),
            'direction': direction,
            'monthly_change': round(monthly_change, 2),
            'data': data
        }

    # ==================== 변동성 ====================

    def calc_volatility(self, sgg_cd: str, period: str) -> Dict[str, Any]:
        """변동성 분석"""
        start_ym, end_ym = self._parse_period(period)
        data = self._get_monthly_data(sgg_cd, start_ym, end_ym)

        values = [d['value'] for d in data if d['value'] > 0]
        n = len(values)

        if n < 2:
            return {'error': '데이터 부족'}

        # 기본 통계
        mean_val = sum(values) / n
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val

        # 표준편차
        variance = sum((v - mean_val) ** 2 for v in values) / (n - 1)
        std_dev = math.sqrt(variance)

        # 변동계수 (CV)
        cv = (std_dev / mean_val * 100) if mean_val > 0 else 0

        # 변동성 등급
        if cv < 5:
            volatility_grade = '안정'
        elif cv < 10:
            volatility_grade = '보통'
        elif cv < 20:
            volatility_grade = '높음'
        else:
            volatility_grade = '매우 불안정'

        # 월별 변동률
        for i, row in enumerate(data):
            if i > 0 and data[i - 1]['value'] > 0:
                prev = data[i - 1]['value']
                curr = row['value']
                row['change_rate'] = round((curr - prev) / prev * 100, 2)
            else:
                row['change_rate'] = 0

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'period': period,
            'mean': round(mean_val),
            'min': round(min_val),
            'max': round(max_val),
            'range': round(range_val),
            'std_dev': round(std_dev),
            'cv': round(cv, 2),
            'grade': volatility_grade,
            'data': data
        }

    # ==================== 계절성 ====================

    def calc_seasonality(self, sgg_cd: str, period: str) -> Dict[str, Any]:
        """계절성 분석"""
        start_ym, end_ym = self._parse_period(period)
        data = self._get_monthly_data(sgg_cd, start_ym, end_ym, metric='volume')

        # 월별 집계
        monthly_avg = {m: [] for m in range(1, 13)}
        for d in data:
            if d['value'] > 0:
                monthly_avg[d['month']].append(d['value'])

        # 월별 평균
        season_data = []
        total_avg = sum(d['value'] for d in data if d['value'] > 0) / max(1, sum(1 for d in data if d['value'] > 0))

        for month in range(1, 13):
            values = monthly_avg[month]
            if values:
                avg = sum(values) / len(values)
                idx = avg / total_avg * 100 if total_avg > 0 else 100
            else:
                avg = 0
                idx = 0

            season_data.append({
                'month': month,
                'avg_volume': round(avg),
                'seasonal_index': round(idx, 1),
                'season': self._get_season(month)
            })

        # 계절별 집계
        seasons = {}
        for sd in season_data:
            season = sd['season']
            if season not in seasons:
                seasons[season] = []
            seasons[season].append(sd['avg_volume'])

        season_summary = {
            s: round(sum(v) / len(v)) if v else 0
            for s, v in seasons.items()
        }

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'period': period,
            'monthly': season_data,
            'seasonal': season_summary,
            'peak_month': max(season_data, key=lambda x: x['avg_volume'])['month'],
            'low_month': min(season_data, key=lambda x: x['avg_volume'] if x['avg_volume'] > 0 else float('inf'))['month']
        }

    def _get_season(self, month: int) -> str:
        """월 → 계절"""
        if month in [3, 4, 5]:
            return '봄'
        elif month in [6, 7, 8]:
            return '여름'
        elif month in [9, 10, 11]:
            return '가을'
        else:
            return '겨울'

    # ==================== 변곡점 ====================

    def find_turning_points(self, sgg_cd: str, period: str, threshold: float = 0.03) -> Dict[str, Any]:
        """변곡점 감지"""
        start_ym, end_ym = self._parse_period(period)
        data = self._get_monthly_data(sgg_cd, start_ym, end_ym)

        if len(data) < 3:
            return {'error': '데이터 부족'}

        # 이동평균 계산 (노이즈 제거)
        for i, row in enumerate(data):
            if i >= 2:
                row['ma3'] = round(sum(data[j]['value'] for j in range(i - 2, i + 1)) / 3)
            else:
                row['ma3'] = row['value']

        # 변곡점 탐지
        turning_points = []
        for i in range(1, len(data) - 1):
            prev = data[i - 1]['ma3']
            curr = data[i]['ma3']
            next_val = data[i + 1]['ma3']

            if prev > 0 and next_val > 0:
                # 저점 (하락 → 상승)
                if prev > curr and curr < next_val:
                    change = (next_val - curr) / curr
                    if change >= threshold:
                        turning_points.append({
                            'ym': data[i]['ym'],
                            'type': '저점',
                            'value': round(curr),
                            'prev_value': round(prev),
                            'next_value': round(next_val),
                            'description': '하락→상승 전환'
                        })

                # 고점 (상승 → 하락)
                elif prev < curr and curr > next_val:
                    change = (curr - next_val) / curr
                    if change >= threshold:
                        turning_points.append({
                            'ym': data[i]['ym'],
                            'type': '고점',
                            'value': round(curr),
                            'prev_value': round(prev),
                            'next_value': round(next_val),
                            'description': '상승→하락 전환'
                        })

        return {
            'region': sgg_cd,
            'region_name': self._get_region_name(sgg_cd),
            'period': period,
            'turning_points': turning_points,
            'count': len(turning_points)
        }

    # ==================== 종합 분석 ====================

    def full_analysis(self, sgg_cd: str, period: str) -> Dict[str, Any]:
        """종합 분석"""
        return {
            'moving_average': self.calc_moving_average(sgg_cd, period),
            'trend': self.calc_trend(sgg_cd, period),
            'volatility': self.calc_volatility(sgg_cd, period),
            'seasonality': self.calc_seasonality(sgg_cd, period),
            'turning_points': self.find_turning_points(sgg_cd, period)
        }


# ==================== 출력 포맷터 ====================

def format_moving_average(data: Dict) -> str:
    """이동평균 마크다운 포맷"""
    windows = data['windows']
    ma_cols = ' | '.join([f'MA{w}' for w in windows])

    lines = [
        f"## 이동평균 분석 ({data['region_name']}, {data['period']})",
        "",
        f"| 년월 | 평균가 | {ma_cols} | 신호 |",
        f"|------|--------|" + '|'.join(['-------' for _ in windows]) + "|------|"
    ]

    for row in reversed(data['data'][-12:]):  # 최근 12개월
        ym_fmt = f"{row['ym'][:4]}.{row['ym'][4:]}"
        value = f"{row['value']:,}" if row['value'] else '-'
        ma_vals = ' | '.join([
            f"{row.get(f'ma{w}', '-'):,}" if row.get(f'ma{w}') else '-'
            for w in windows
        ])
        signal = row.get('signal', '-')
        lines.append(f"| {ym_fmt} | {value} | {ma_vals} | {signal} |")

    return "\n".join(lines)


def format_trend(data: Dict) -> str:
    """추세선 마크다운 포맷"""
    direction_sign = '+' if data['monthly_change'] >= 0 else ''
    return "\n".join([
        f"## 추세 분석 ({data['region_name']}, {data['period']})",
        "",
        "| 지표 | 값 |",
        "|------|-----|",
        f"| 추세 방향 | {data['direction']} |",
        f"| 월평균 변화율 | {direction_sign}{data['monthly_change']}% |",
        f"| 기울기 | {data['slope']:,}만원/월 |",
        f"| 결정계수 (R²) | {data['r_squared']} |"
    ])


def format_volatility(data: Dict) -> str:
    """변동성 마크다운 포맷"""
    return "\n".join([
        f"## 변동성 분석 ({data['region_name']}, {data['period']})",
        "",
        "| 지표 | 값 |",
        "|------|-----|",
        f"| 평균가 | {data['mean']:,}만원 |",
        f"| 최저가 | {data['min']:,}만원 |",
        f"| 최고가 | {data['max']:,}만원 |",
        f"| 변동폭 | {data['range']:,}만원 |",
        f"| 표준편차 | {data['std_dev']:,}만원 |",
        f"| 변동계수 (CV) | {data['cv']}% |",
        f"| 변동성 등급 | {data['grade']} |"
    ])


def format_seasonality(data: Dict) -> str:
    """계절성 마크다운 포맷"""
    lines = [
        f"## 계절성 분석 ({data['region_name']}, {data['period']})",
        "",
        "### 월별 거래량 패턴",
        "",
        "| 월 | 평균 거래량 | 계절지수 | 계절 |",
        "|-----|------------|----------|------|"
    ]

    for m in data['monthly']:
        lines.append(
            f"| {m['month']:2d}월 | {m['avg_volume']:,}건 | {m['seasonal_index']}% | {m['season']} |"
        )

    lines.extend([
        "",
        "### 계절별 평균",
        "",
        "| 계절 | 평균 거래량 |",
        "|------|------------|"
    ])

    for season in ['봄', '여름', '가을', '겨울']:
        if season in data['seasonal']:
            lines.append(f"| {season} | {data['seasonal'][season]:,}건 |")

    lines.extend([
        "",
        f"**성수기**: {data['peak_month']}월 / **비수기**: {data['low_month']}월"
    ])

    return "\n".join(lines)


def format_turning_points(data: Dict) -> str:
    """변곡점 마크다운 포맷"""
    lines = [
        f"## 변곡점 분석 ({data['region_name']}, {data['period']})",
        "",
        f"**감지된 변곡점**: {data['count']}개",
        ""
    ]

    if data['turning_points']:
        lines.extend([
            "| 시점 | 유형 | 가격 | 설명 |",
            "|------|------|------|------|"
        ])
        for tp in data['turning_points']:
            ym_fmt = f"{tp['ym'][:4]}.{tp['ym'][4:]}"
            lines.append(
                f"| {ym_fmt} | {tp['type']} | {tp['value']:,}만원 | {tp['description']} |"
            )
    else:
        lines.append("분석 기간 내 유의미한 변곡점이 감지되지 않음")

    return "\n".join(lines)


def format_full_analysis(data: Dict) -> str:
    """종합 분석 마크다운 포맷"""
    ma = data['moving_average']
    region_name = ma['region_name']
    period = ma['period']

    parts = [
        f"# 아파트 시계열 트렌드 분석: {region_name}",
        f"**분석 기간**: {period}",
        "",
        "---",
        "",
        format_moving_average(data['moving_average']),
        "",
        "---",
        "",
        format_trend(data['trend']),
        "",
        "---",
        "",
        format_volatility(data['volatility']),
        "",
        "---",
        "",
        format_seasonality(data['seasonality']),
        "",
        "---",
        "",
        format_turning_points(data['turning_points'])
    ]

    return "\n".join(parts)


# ==================== CLI ====================

def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='아파트 시계열 트렌드 분석',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 명령
    parser.add_argument('--ma', type=str, help='이동평균 (개월, 쉼표 구분)')
    parser.add_argument('--trend', type=str, choices=['linear', 'poly2', 'poly3'], help='추세선')
    parser.add_argument('--volatility', action='store_true', help='변동성 분석')
    parser.add_argument('--seasonality', action='store_true', help='계절성 분석')
    parser.add_argument('--turning-points', action='store_true', help='변곡점 감지')
    parser.add_argument('--full', action='store_true', help='종합 분석')

    # 옵션
    parser.add_argument('--region', '-r', type=str, required=True, help='지역코드')
    parser.add_argument('--period', type=str, required=True, help='기간 (YYYYMM-YYYYMM)')
    parser.add_argument('--metric', type=str, default='price', choices=['price', 'volume'], help='분석 대상')
    parser.add_argument('--output', '-o', type=str, help='결과 저장 파일')
    parser.add_argument('--db', type=str, help='DB 파일 경로')

    args = parser.parse_args()

    trend = AptTrend(args.db)

    try:
        output = ""

        if args.ma:
            windows = [int(w.strip()) for w in args.ma.split(',')]
            data = trend.calc_moving_average(args.region, args.period, windows)
            output = format_moving_average(data)

        elif args.trend:
            data = trend.calc_trend(args.region, args.period, args.trend)
            output = format_trend(data)

        elif args.volatility:
            data = trend.calc_volatility(args.region, args.period)
            output = format_volatility(data)

        elif args.seasonality:
            data = trend.calc_seasonality(args.region, args.period)
            output = format_seasonality(data)

        elif args.turning_points:
            data = trend.find_turning_points(args.region, args.period)
            output = format_turning_points(data)

        elif args.full:
            data = trend.full_analysis(args.region, args.period)
            output = format_full_analysis(data)

        else:
            parser.print_help()
            return

        print(output)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n[저장됨] {args.output}")

    finally:
        trend.close()


if __name__ == '__main__':
    main()
