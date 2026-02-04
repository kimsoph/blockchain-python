# -*- coding: utf-8 -*-
"""
utils.py 테스트

날짜/나이 계산 유틸리티 함수들을 테스트합니다.
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.utils import (
    calculate_age,
    calculate_years,
    date_to_yyyymm,
    calculate_interval_years,
    convert_birth_date,
    calculate_impi_date
)
from core.exceptions import DateConversionError


class TestCalculateAge:
    """calculate_age 함수 테스트"""

    def test_basic_age_calculation(self):
        """기본 나이 계산"""
        result = calculate_age(198001, 202601)
        assert result == 46.0

    def test_partial_year(self):
        """반년 포함 나이 계산"""
        result = calculate_age(198007, 202601)
        assert result == 45.5

    def test_invalid_input_returns_none(self):
        """잘못된 입력시 None 반환"""
        result = calculate_age("invalid", 202601)
        assert result is None

    def test_strict_mode_raises_exception(self):
        """strict=True일 때 예외 발생"""
        with pytest.raises(DateConversionError):
            calculate_age("invalid", 202601, strict=True)

    def test_strict_mode_normal_operation(self):
        """strict=True일 때 정상 동작"""
        result = calculate_age(198001, 202601, strict=True)
        assert result == 46.0


class TestCalculateYears:
    """calculate_years 함수 테스트"""

    def test_basic_years_calculation(self):
        """기본 연차 계산"""
        result = calculate_years(200301, 202601)
        assert result == 23.0

    def test_partial_year(self):
        """반년 포함 연차 계산"""
        result = calculate_years(200307, 202601)
        assert result == 22.5

    def test_invalid_input_returns_none(self):
        """잘못된 입력시 None 반환"""
        result = calculate_years("invalid", 202601)
        assert result is None

    def test_strict_mode_raises_exception(self):
        """strict=True일 때 예외 발생"""
        with pytest.raises(DateConversionError):
            calculate_years("invalid", 202601, strict=True)


class TestDateToYYYYMM:
    """date_to_yyyymm 함수 테스트"""

    def test_iso_format(self):
        """ISO 형식 변환"""
        result = date_to_yyyymm("2020-01-15")
        assert result == 202001

    def test_yyyymm_format(self):
        """YYYYMM 형식 통과"""
        result = date_to_yyyymm("202001")
        assert result == 202001

    def test_none_input(self):
        """None 입력"""
        result = date_to_yyyymm(None)
        assert result is None

    def test_invalid_input_returns_none(self):
        """잘못된 입력시 None 반환"""
        result = date_to_yyyymm("invalid")
        assert result is None

    def test_strict_mode_raises_exception(self):
        """strict=True일 때 예외 발생"""
        with pytest.raises(DateConversionError):
            date_to_yyyymm("invalid", strict=True)


class TestCalculateIntervalYears:
    """calculate_interval_years 함수 테스트"""

    def test_basic_interval(self):
        """기본 간격 계산"""
        result = calculate_interval_years(202001, 202301)
        assert result == 3.0

    def test_partial_year_interval(self):
        """반년 간격 계산"""
        result = calculate_interval_years(202001, 202007)
        assert result == 0.5

    def test_negative_interval_returns_none(self):
        """역순 간격은 None 반환"""
        result = calculate_interval_years(202301, 202001)
        assert result is None

    def test_strict_mode_raises_exception(self):
        """strict=True일 때 예외 발생"""
        with pytest.raises(DateConversionError):
            calculate_interval_years("invalid", 202001, strict=True)


class TestConvertBirthDate:
    """convert_birth_date 함수 테스트"""

    def test_6digit_format(self):
        """6자리 YYMMDD 형식"""
        result = convert_birth_date(620627, 202601)
        assert result == 196206

    def test_2000s_generation(self):
        """2000년대생 (3자리)"""
        result = convert_birth_date(306, 202601)
        assert result == 200306

    def test_5digit_2000s(self):
        """5자리 2000년대생"""
        result = convert_birth_date(20125, 202601)
        assert result == 200201

    def test_with_actual_birth_date(self):
        """실제생년월일 참조"""
        result = convert_birth_date(306, 202601, "2003-06-15")
        assert result == 200306

    def test_none_input(self):
        """None 입력"""
        result = convert_birth_date(None, 202601)
        assert result is None

    def test_strict_mode_raises_exception(self):
        """strict=True일 때 예외 발생"""
        with pytest.raises(DateConversionError):
            convert_birth_date("invalid", 202601, strict=True)


class TestCalculateImpiDate:
    """calculate_impi_date 함수 테스트"""

    def test_first_half_year(self):
        """상반기 출생 -> 1월 임피"""
        result = calculate_impi_date(196803)
        assert result == 202501

    def test_second_half_year(self):
        """하반기 출생 -> 7월 임피"""
        result = calculate_impi_date(196808)
        assert result == 202507

    def test_none_input(self):
        """None 입력"""
        result = calculate_impi_date(None)
        assert result is None
