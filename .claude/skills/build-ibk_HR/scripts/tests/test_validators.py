# -*- coding: utf-8 -*-
"""
validators.py 테스트

DataValidator 클래스의 검증 로직을 테스트합니다.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.validators import DataValidator, ValidationRule
from core.config import Config


class TestValidationRule:
    """ValidationRule 클래스 테스트"""

    def test_basic_rule_creation(self):
        """기본 규칙 생성 테스트"""
        rule = ValidationRule(
            name="테스트_규칙",
            check=lambda r: r.get('value') is None
        )
        assert rule.name == "테스트_규칙"

    def test_rule_with_custom_message(self):
        """커스텀 메시지 규칙 테스트"""
        rule = ValidationRule(
            name="범위초과",
            check=lambda r: r.get('age', 0) < 16,
            message=lambda r: f"범위초과({r.get('age')}세)"
        )
        row = pd.Series({'age': 10})
        assert rule.check(row) == True  # np.True_ 호환성을 위해 == 사용
        assert rule.get_error_message(row) == "범위초과(10세)"

    def test_default_error_message(self):
        """기본 에러 메시지 테스트"""
        rule = ValidationRule(
            name="필수값_누락",
            check=lambda r: True
        )
        row = pd.Series({})
        assert rule.get_error_message(row) == "필수값_누락"


class TestDataValidatorEmployee:
    """직원 데이터 검증 테스트"""

    def test_validate_employee_skips_executive(self, validator, sample_employee_df):
        """임원실 그룹은 검증을 건너뛰는지 테스트"""
        result = validator.validate_employee_data(sample_employee_df)

        # 임원실 행(index 2)은 오류가 없어야 함
        executive_row = result[result['그룹'] == '임원실'].iloc[0]
        assert executive_row['오류여부'] == 0

    def test_validate_employee_detects_missing_birth(self, validator):
        """출생년월 누락 감지 테스트"""
        df = pd.DataFrame({
            '그룹': ['영업그룹'],
            '실제생년월일': [None],
            '출생년월': [None],
            '입행년월': [200301],
            '현재나이': [None],
            '입행나이': [None],
        })
        result = validator.validate_employee_data(df)

        assert result.iloc[0]['오류여부'] == 1
        assert '출생년월_누락' in result.iloc[0]['오류사유']

    def test_validate_employee_detects_age_range_error(self, validator):
        """나이 범위 초과 감지 테스트"""
        df = pd.DataFrame({
            '그룹': ['영업그룹'],
            '실제생년월일': ['1980-01-15'],
            '출생년월': [198001],
            '입행년월': [200301],
            '현재나이': [10.0],  # MIN_AGE(16) 미만
            '입행나이': [23.0],
        })
        result = validator.validate_employee_data(df)

        assert result.iloc[0]['오류여부'] == 1
        assert '현재나이_범위초과' in result.iloc[0]['오류사유']

    def test_validate_employee_detects_join_before_birth(self, validator):
        """입행년월이 출생년월보다 이전인 경우 감지 테스트"""
        df = pd.DataFrame({
            '그룹': ['영업그룹'],
            '실제생년월일': ['1990-01-15'],
            '출생년월': [199001],
            '입행년월': [198501],  # 출생년월보다 이전
            '현재나이': [36.0],
            '입행나이': [None],
        })
        result = validator.validate_employee_data(df)

        assert result.iloc[0]['오류여부'] == 1
        assert '입행년월이_출생년월보다_이전' in result.iloc[0]['오류사유']

    def test_validate_employee_normal_data(self, validator):
        """정상 데이터 검증 테스트"""
        df = pd.DataFrame({
            '그룹': ['영업그룹'],
            '실제생년월일': ['1980-01-15'],
            '출생년월': [198001],
            '입행년월': [200301],
            '현재나이': [46.0],
            '입행나이': [23.0],
        })
        result = validator.validate_employee_data(df)

        assert result.iloc[0]['오류여부'] == 0
        assert result.iloc[0]['오류사유'] == ''


class TestDataValidatorPromotion:
    """승진 데이터 검증 테스트"""

    def test_validate_promotion_missing_id(self, validator):
        """직번 누락 감지 테스트"""
        df = pd.DataFrame({
            '직번': [None],
            '이름': ['홍길동'],
            '승진직급': ['승1'],
            '승진년월': ['202001'],
        })
        result = validator.validate_promotion_data(df, Config.PROMOTION_ORDER)

        assert result.iloc[0]['오류여부'] == 1
        assert '직번_누락' in result.iloc[0]['오류사유']

    def test_validate_promotion_invalid_date_format(self, validator):
        """승진년월 형식 오류 감지 테스트"""
        df = pd.DataFrame({
            '직번': [1001],
            '이름': ['홍길동'],
            '승진직급': ['승1'],
            '승진년월': ['invalid'],
        })
        result = validator.validate_promotion_data(df, Config.PROMOTION_ORDER)

        assert result.iloc[0]['오류여부'] == 1
        assert '승진년월_형식오류' in result.iloc[0]['오류사유']

    def test_validate_promotion_invalid_position(self, validator):
        """정의되지 않은 승진직급 감지 테스트"""
        df = pd.DataFrame({
            '직번': [1001],
            '이름': ['홍길동'],
            '승진직급': ['미정의직급'],
            '승진년월': ['202001'],
        })
        result = validator.validate_promotion_data(df, Config.PROMOTION_ORDER)

        assert result.iloc[0]['오류여부'] == 1
        assert '승진직급_미정의' in result.iloc[0]['오류사유']


class TestDataValidatorCEO:
    """CEO 데이터 검증 테스트"""

    def test_validate_ceo_missing_name(self, validator):
        """이름 누락 감지 테스트"""
        df = pd.DataFrame({
            '직위': ['은행장'],
            '이름': [''],
            '취임일자': ['2020-01-01'],
            '취임년월': [202001],
        })
        result = validator.validate_ceo_data(df)

        assert result.iloc[0]['오류여부'] == 1
        assert '이름_누락' in result.iloc[0]['오류사유']

    def test_validate_ceo_missing_appointment_date(self, validator):
        """취임일자 누락 감지 테스트"""
        df = pd.DataFrame({
            '직위': ['은행장'],
            '이름': ['이사장'],
            '취임일자': [None],
            '취임년월': [None],
        })
        result = validator.validate_ceo_data(df)

        assert result.iloc[0]['오류여부'] == 1
        assert '취임일자_누락' in result.iloc[0]['오류사유']
