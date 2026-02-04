#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metric_parser.py - IBK 경영지표 파싱 모듈

textBook 마크다운에서 추출된 텍스트에서 지표명과 수치를 파싱합니다.
"""

import re
from typing import Optional, Tuple, Dict, Any


class MetricParser:
    """경영지표 텍스트 파싱 클래스"""

    # 지표명 정규식 패턴
    METRIC_PATTERNS = {
        # 수익성 지표
        '당기순이익': r'당기순이익[:\s]*([0-9,.]+)\s*(억원|조원)',
        'ROA': r'ROA[:\s]*([0-9.]+)\s*%',
        'ROE': r'ROE[:\s]*([0-9.]+)\s*%',
        'NIM': r'NIM[:\s]*([0-9.]+)\s*%',
        # 건전성 지표
        '고정이하여신비율': r'고정이하여신비율[:\s]*([0-9.]+)\s*%',
        '연체율': r'연체율[(\s표면)]*[:\s]*([0-9.]+)\s*%',
        'Coverage Ratio': r'Coverage\s*Ratio[:\s]*([0-9.]+)\s*%',
        # 자본적정성 지표
        'BIS비율': r'BIS[자기자본]*비율[:\s]*([0-9.]+)\s*%',
        'CET1비율': r'CET1비율[:\s]*([0-9.]+)\s*%',
        # 성장성 지표
        '총자산': r'총자산[:\s]*([0-9,.]+)\s*(억원|조원)',
        '중소기업대출': r'중소기업대출[:\s]*([0-9,.]+)\s*(억원|조원)',
        '총수신': r'총수신[:\s]*([0-9,.]+)\s*(억원|조원)',
    }

    # 변동 패턴
    CHANGE_PATTERNS = [
        r'전[기년분]?\s*대비\s*([+\-△▲▼]?)\s*([0-9,.]+)\s*(억원|조원|%|%p|bp)?',
        r'([+\-△▲▼])\s*([0-9,.]+)\s*(억원|조원|%|%p|bp)?',
        r'증감\s*([+\-△▲▼]?)\s*([0-9,.]+)',
    ]

    @staticmethod
    def parse_number(text: str, unit: str = None) -> Optional[float]:
        """
        숫자 텍스트를 float로 변환

        Args:
            text: 숫자 텍스트 (예: "21,050", "447.5")
            unit: 단위 (억원, 조원, %, bp 등)

        Returns:
            파싱된 숫자 또는 None
        """
        if not text:
            return None

        # 쉼표 제거
        cleaned = text.replace(',', '').strip()

        try:
            value = float(cleaned)

            # 단위 변환 (조원 → 억원으로 통일하지 않음, 원본 유지)
            # 필요 시 호출부에서 변환

            return value
        except ValueError:
            return None

    @staticmethod
    def parse_change_sign(sign: str) -> int:
        """
        변동 부호 파싱

        Args:
            sign: 부호 문자 (+, -, △, ▲, ▼)

        Returns:
            1 (증가), -1 (감소), 0 (변동 없음)
        """
        if sign in ['+', '▲']:
            return 1
        elif sign in ['-', '△', '▼']:
            return -1
        return 0

    def extract_metric(self, text: str, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        텍스트에서 특정 지표 추출

        Args:
            text: 검색할 텍스트
            metric_name: 지표명 (예: 'ROA', '당기순이익')

        Returns:
            {'value': float, 'unit': str} 또는 None
        """
        if metric_name not in self.METRIC_PATTERNS:
            return None

        pattern = self.METRIC_PATTERNS[metric_name]
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return None

        groups = match.groups()
        value = self.parse_number(groups[0])

        if value is None:
            return None

        unit = groups[1] if len(groups) > 1 else '%'

        return {
            'name': metric_name,
            'value': value,
            'unit': unit,
            'raw_text': match.group(0)
        }

    def extract_all_metrics(self, text: str) -> list:
        """
        텍스트에서 모든 인식 가능한 지표 추출

        Args:
            text: 검색할 텍스트

        Returns:
            추출된 지표 목록
        """
        results = []
        for metric_name in self.METRIC_PATTERNS:
            result = self.extract_metric(text, metric_name)
            if result:
                results.append(result)
        return results

    def extract_with_change(self, text: str, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        지표와 변동 정보를 함께 추출

        Args:
            text: 검색할 텍스트
            metric_name: 지표명

        Returns:
            {'value': float, 'unit': str, 'change': float, 'change_unit': str} 또는 None
        """
        base = self.extract_metric(text, metric_name)
        if not base:
            return None

        # 변동 정보 추출
        for pattern in self.CHANGE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                sign = self.parse_change_sign(groups[0] if groups[0] else '')
                change_value = self.parse_number(groups[1])
                change_unit = groups[2] if len(groups) > 2 and groups[2] else '%'

                if change_value is not None:
                    base['change'] = change_value * (sign if sign else 1)
                    base['change_unit'] = change_unit
                    break

        return base


def extract_period_from_filename(filename: str) -> Optional[str]:
    """
    파일명에서 기간 정보 추출

    Args:
        filename: 파일명 (예: 'textBook_202510_clean.md')

    Returns:
        기간 문자열 (예: '202510') 또는 None
    """
    match = re.search(r'(\d{6})', filename)
    return match.group(1) if match else None


def format_period(period: str) -> str:
    """
    기간 문자열 포맷팅

    Args:
        period: 기간 (예: '202510')

    Returns:
        포맷된 기간 (예: '2025.10')
    """
    if len(period) == 6:
        return f"{period[:4]}.{period[4:]}"
    return period


if __name__ == '__main__':
    # 테스트
    parser = MetricParser()

    test_text = """
    당기순이익: 21,050억원 (전기 대비 △3,231억원)
    ROA: 0.58% (+0.02%p)
    BIS비율: 14.89% (전년말 대비 +0.20%p)
    총자산: 447.5조원 (전기 대비 +16.2조원)
    """

    print("=== 지표 추출 테스트 ===")
    for metric_name in ['당기순이익', 'ROA', 'BIS비율', '총자산']:
        result = parser.extract_with_change(test_text, metric_name)
        print(f"{metric_name}: {result}")

    print("\n=== 기간 추출 테스트 ===")
    print(extract_period_from_filename('textBook_202510_clean.md'))
    print(format_period('202510'))
