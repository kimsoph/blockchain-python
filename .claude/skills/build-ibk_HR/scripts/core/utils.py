# -*- coding: utf-8 -*-
"""
IBK HR 데이터 처리 유틸리티 함수

날짜/나이 계산 및 변환 함수들을 제공합니다.
strict 모드 지원으로 테스트 시 명시적 에러 처리가 가능합니다.
"""

import pandas as pd
from typing import Optional, Union
import logging

from core.exceptions import DateConversionError, DataValidationError

logger = logging.getLogger(__name__)


def calculate_age(birth_date: Union[int, str], reference_date: int = 202601,
                  *, strict: bool = False) -> Optional[float]:
    """나이 계산

    Args:
        birth_date: 생년월일 (YYYYMM 형식)
        reference_date: 기준일자 (YYYYMM 형식)
        strict: True일 경우 변환 실패 시 예외 발생

    Returns:
        계산된 나이 (소수점 1자리)

    Raises:
        DateConversionError: strict=True이고 날짜 변환 실패 시
    """
    try:
        birth_year = int(str(birth_date)[:4])
        birth_month = int(str(birth_date)[4:6])
        ref_year = int(str(reference_date)[:4])
        ref_month = int(str(reference_date)[4:6])

        # 월 차이를 기반으로 정확한 나이 계산
        total_months = (ref_year - birth_year) * 12 + (ref_month - birth_month)
        return round(total_months / 12, 1)
    except Exception as e:
        logger.debug(f"Age calculation failed for {birth_date}: {e}")
        if strict:
            raise DateConversionError(birth_date, "YYYYMM")
        return None


def calculate_years(start_date: Union[int, str], reference_date: int = 202601,
                    *, strict: bool = False) -> Optional[float]:
    """연차 계산

    Args:
        start_date: 시작일자 (YYYYMM 형식)
        reference_date: 기준일자 (YYYYMM 형식)
        strict: True일 경우 변환 실패 시 예외 발생

    Returns:
        계산된 연차 (소수점 1자리)

    Raises:
        DateConversionError: strict=True이고 날짜 변환 실패 시
    """
    try:
        start_year = int(str(start_date)[:4])
        start_month = int(str(start_date)[4:6])
        ref_year = int(str(reference_date)[:4])
        ref_month = int(str(reference_date)[4:6])

        years = ref_year - start_year
        months = ref_month - start_month
        return round(years + months/12, 1)
    except Exception as e:
        logger.debug(f"Years calculation failed for {start_date}: {e}")
        if strict:
            raise DateConversionError(start_date, "YYYYMM")
        return None


def date_to_yyyymm(date_str: Union[str, pd.Timestamp, None],
                   *, strict: bool = False) -> Optional[int]:
    """날짜를 YYYYMM 형식으로 변환

    Args:
        date_str: 변환할 날짜 문자열
        strict: True일 경우 변환 실패 시 예외 발생

    Returns:
        YYYYMM 형식의 정수

    Raises:
        DateConversionError: strict=True이고 변환 실패 시
    """
    try:
        if pd.isna(date_str):
            return None
        date_str = str(date_str)
        if '-' in date_str:
            date_obj = pd.to_datetime(date_str)
            return int(date_obj.strftime('%Y%m'))
        return int(date_str[:6])
    except Exception as e:
        logger.debug(f"Date conversion failed for {date_str}: {e}")
        if strict:
            raise DateConversionError(date_str)
        return None


def calculate_interval_years(start_yyyymm: Union[int, str], end_yyyymm: Union[int, str],
                             *, strict: bool = False) -> Optional[float]:
    """두 날짜 간의 연차 계산

    Args:
        start_yyyymm: 시작 날짜 (YYYYMM)
        end_yyyymm: 종료 날짜 (YYYYMM)
        strict: True일 경우 변환 실패 시 예외 발생

    Returns:
        년 단위 차이 (소수점 1자리)

    Raises:
        DateConversionError: strict=True이고 변환 실패 시
    """
    try:
        start_year = int(str(start_yyyymm)[:4])
        start_month = int(str(start_yyyymm)[4:6])
        end_year = int(str(end_yyyymm)[:4])
        end_month = int(str(end_yyyymm)[4:6])

        months_diff = (end_year - start_year) * 12 + (end_month - start_month)
        return round(months_diff / 12, 1) if months_diff > 0 else None
    except Exception as e:
        logger.debug(f"Interval calculation failed between {start_yyyymm} and {end_yyyymm}: {e}")
        if strict:
            raise DateConversionError(f"{start_yyyymm}~{end_yyyymm}", "YYYYMM")
        return None


def convert_birth_date(short_date: Union[int, str], reference_date: int = 202601,
                       actual_birth_date: str = None, *, strict: bool = False) -> Optional[int]:
    """축약된 출생년월을 전체 연도 형식으로 변환

    Args:
        short_date: 축약된 출생년월일 (예: 620627, 306, 20125 등)
        reference_date: 기준년월 (YYYYMM 형식)
        actual_birth_date: 실제생년월일 (애매한 경우 참고용, YYYY-MM-DD 형식)
        strict: True일 경우 변환 실패 시 예외 발생

    Returns:
        변환된 출생년월 (YYYYMM 형식, 예: 196206)

    Raises:
        DateConversionError: strict=True이고 변환 실패 시

    변환 로직:
    1. 6자리: YYMMDD 형태 -> YYMM만 추출 (예: 620627 -> 6206)
    2. 3~5자리: 실제생년월일을 참고하여 변환
    3. 실제생년월일이 없으면 추정 로직 사용
    """
    try:
        if pd.isna(short_date):
            return None

        # 문자열로 변환
        short_date_str = str(int(short_date))

        # 3~5자리이고 실제생년월일이 있는 경우, 실제생년월일 사용
        if len(short_date_str) in [3, 4, 5] and actual_birth_date and not pd.isna(actual_birth_date):
            try:
                # 실제생년월일에서 년월 추출
                actual_date = pd.to_datetime(actual_birth_date)
                return int(actual_date.strftime('%Y%m'))
            except:
                pass  # 실제생년월일 파싱 실패시 기존 로직 사용

        # 자리수에 따른 처리
        if len(short_date_str) == 6:
            # 6자리: YYMMDD 형태 -> YYMM만 추출
            short_date_str = short_date_str[:4]  # 620627 -> 6206
        elif len(short_date_str) == 5:
            # 5자리: YMMDD 형태 (2000년대생)
            # 첫 자리가 년도의 마지막 자리, 다음 두 자리가 월
            year_digit = short_date_str[0]  # 2, 3, 4 등
            month = short_date_str[1:3]  # 01, 11 등
            short_date_str = f"0{year_digit}{month}"  # 20125 -> 0201
        elif len(short_date_str) == 3:
            # 3자리: YMD 또는 YMM 형태 (2000년대생)
            # 첫 자리가 년도의 마지막 자리
            year_digit = short_date_str[0]  # 3 등
            month = short_date_str[1:3] if len(short_date_str[1:]) == 2 else f"0{short_date_str[1]}"
            short_date_str = f"0{year_digit}{month}"  # 306 -> 0306
        elif len(short_date_str) == 4 and int(short_date_str) < 1300:
            # 4자리이면서 1300 미만: MMDD 형태 (2000년대생)
            if short_date_str[:2] in ['10', '11', '12']:
                # 10, 11, 12월
                short_date_str = f"00{short_date_str[:2]}"  # 1026 -> 0010
            else:
                # 1~9월 (첫자리가 월)
                month = short_date_str[0].zfill(2)
                short_date_str = f"00{month}"  # 126 -> 0001
        # 이미 4자리 YYMM 형태인 경우는 그대로 유지

        # 정수로 변환
        short_date_int = int(short_date_str)

        # YYMM 형태를 YYYYMM으로 변환
        # 2000년대: 0001 ~ 2512 범위
        # 1900년대: 5001 ~ 9912 범위
        if short_date_int < 3000:  # 00년~29년은 2000년대로 간주
            converted_date = short_date_int + 200000
        else:  # 30년~99년은 1900년대로 간주
            converted_date = short_date_int + 190000

        return converted_date
    except Exception as e:
        logger.debug(f"Birth date conversion failed for {short_date}: {e}")
        if strict:
            raise DateConversionError(short_date, "YYMMDD or YYYYMM")
        return None


def calculate_impi_date(birth_date: Union[int, str]) -> Optional[int]:
    """임피년월 계산 (만 57세가 되는 년월)

    만 57세가 되는 년월을 계산하되,
    1~6월이면 1월, 7~12월이면 7월로 설정

    Args:
        birth_date: 출생년월 (YYYYMM 형식)

    Returns:
        임피년월 (YYYYMM 형식)
    """
    if pd.isna(birth_date):
        return None

    try:
        birth_year = int(str(int(birth_date))[:4])
        birth_month = int(str(int(birth_date))[4:6])

        # 만 57세가 되는 년월 계산
        impi_year = birth_year + 57
        impi_month = birth_month

        # 1~6월은 1월, 7~12월은 7월로 조정
        if impi_month <= 6:
            impi_month = 1
        else:
            impi_month = 7

        return int(f"{impi_year:04d}{impi_month:02d}")
    except:
        return None
