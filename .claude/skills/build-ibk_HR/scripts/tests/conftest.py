# -*- coding: utf-8 -*-
"""
pytest 공통 설정 및 픽스처

테스트 전반에서 사용하는 공통 fixture들을 정의합니다.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.validators import DataValidator


@pytest.fixture
def config():
    """기본 Config 인스턴스"""
    return Config(reference_date=202601)


@pytest.fixture
def validator():
    """기본 DataValidator 인스턴스"""
    return DataValidator()


@pytest.fixture
def sample_employee_df():
    """테스트용 직원 데이터프레임"""
    return pd.DataFrame({
        '직번': [1001, 1002, 1003, 1004],
        '이름': ['홍길동', '김철수', '이영희', '박민수'],
        '그룹': ['영업그룹', '영업그룹', '임원실', 'IT그룹'],
        '실제생년월일': ['1980-01-15', '1990-05-20', None, '1985-03-10'],
        '출생년월': [198001, 199005, None, 198503],
        '입행년월': [200301, 201501, None, 200901],
        '현재나이': [46.0, 35.7, None, 40.8],
        '입행나이': [23.2, 24.8, None, 23.5],
    })


@pytest.fixture
def sample_promotion_df():
    """테스트용 승진 데이터프레임"""
    return pd.DataFrame({
        '직번': [1001, 1002, 1003, None],
        '이름': ['홍길동', '김철수', '', '박민수'],
        '승진직급': ['승1', '승2', '승3', '승0'],
        '승진년월': ['202001', '202101', '202201', 'invalid'],
        '승진부점': ['서울지점', '부산지점', '대전지점', '광주지점'],
    })


@pytest.fixture
def sample_ceo_df():
    """테스트용 CEO 데이터프레임"""
    return pd.DataFrame({
        '직위': ['은행장', '부행장', ''],
        '기수': [1, 2, 3],
        '이름': ['이사장', '', '김감사'],
        '취임일자': ['2020-01-01', '2021-06-15', None],
        '취임년월': [202001, 202106, None],
    })


@pytest.fixture
def employee_with_errors_df():
    """오류가 있는 직원 데이터프레임 (검증 테스트용)"""
    return pd.DataFrame({
        '직번': [1001, 1002, 1003],
        '이름': ['홍길동', '김철수', '이영희'],
        '그룹': ['영업그룹', '영업그룹', '영업그룹'],
        '실제생년월일': ['1980-01-15', None, '1970-01-01'],
        '출생년월': [198001, None, 197001],
        '입행년월': [200301, 201501, 196501],  # 마지막은 출생년월보다 이전
        '현재나이': [46.0, None, 10.0],  # 마지막은 범위 초과
        '입행나이': [23.2, None, 75.0],  # 마지막은 범위 초과
    })
