# -*- coding: utf-8 -*-
"""
IBK HR 데이터 검증 모듈

ValidationRule 패턴을 사용하여 직원, 승진, CEO 데이터의 유효성을 검증합니다.
"""

import pandas as pd
from dataclasses import dataclass
from typing import List, Callable, Optional
import logging

from core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """검증 규칙 정의

    Attributes:
        name: 규칙 이름 (오류 사유에 표시)
        check: 검증 함수 (행을 받아 True면 오류)
        message: 상세 메시지 생성 함수 (선택)
    """
    name: str
    check: Callable[[pd.Series], bool]
    message: Optional[Callable[[pd.Series], str]] = None

    def get_error_message(self, row: pd.Series) -> str:
        """오류 메시지 생성"""
        if self.message:
            return self.message(row)
        return self.name


class DataValidator:
    """데이터 검증 클래스

    ValidationRule 패턴을 사용하여 중복 코드를 제거하고
    일관된 검증 프로세스를 제공합니다.
    """

    def _validate_dataframe(
        self,
        df: pd.DataFrame,
        rules: List[ValidationRule],
        skip_condition: Optional[Callable[[pd.Series], bool]] = None,
        data_type: str = "데이터"
    ) -> pd.DataFrame:
        """공통 검증 로직

        Args:
            df: 검증할 데이터프레임
            rules: 적용할 검증 규칙 목록
            skip_condition: 검증을 건너뛸 조건 (해당 행은 정상 처리)
            data_type: 로깅용 데이터 타입명

        Returns:
            오류여부, 오류사유 컬럼이 추가된 데이터프레임
        """
        logger.info(f"{data_type} 검증 시작")

        def validate_row(row: pd.Series) -> tuple:
            """단일 행 검증 (apply용)"""
            # 검증 제외 조건 확인
            if skip_condition and skip_condition(row):
                return (0, '')

            # 모든 규칙 적용
            error_reasons = []
            for rule in rules:
                try:
                    if rule.check(row):
                        error_reasons.append(rule.get_error_message(row))
                except Exception as e:
                    logger.debug(f"규칙 '{rule.name}' 검증 중 예외: {e}")

            if error_reasons:
                return (1, '; '.join(error_reasons))
            return (0, '')

        # apply로 벡터화된 검증 수행
        results = df.apply(validate_row, axis=1, result_type='expand')
        df['오류여부'] = results[0]
        df['오류사유'] = results[1]

        error_count = df['오류여부'].sum()
        normal_count = len(df) - error_count

        logger.info(f"{data_type} 검증 완료: 정상 {normal_count}건, 오류 {error_count}건")

        return df

    def validate_employee_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """직원 데이터 검증 및 오류여부 컬럼 추가

        Args:
            df: 검증할 직원 데이터프레임

        Returns:
            오류여부 컬럼이 추가된 데이터프레임 (오류:1, 정상:0)
        """
        rules = [
            ValidationRule(
                name="출생년월_누락",
                check=lambda r: pd.isna(r.get('실제생년월일')) or r.get('출생년월') is None
            ),
            ValidationRule(
                name="입행년월_누락",
                check=lambda r: pd.isna(r.get('입행년월')) or r.get('입행년월') is None
            ),
            ValidationRule(
                name="현재나이_범위초과",
                check=lambda r: (
                    pd.notna(r.get('현재나이')) and
                    (r.get('현재나이') < Config.MIN_AGE or r.get('현재나이') > Config.MAX_AGE)
                ),
                message=lambda r: f"현재나이_범위초과({r.get('현재나이')}세)"
            ),
            ValidationRule(
                name="입행나이_범위초과",
                check=lambda r: (
                    pd.notna(r.get('입행나이')) and
                    (r.get('입행나이') < Config.MIN_AGE or r.get('입행나이') > Config.MAX_JOIN_AGE)
                ),
                message=lambda r: f"입행나이_범위초과({r.get('입행나이')}세)"
            ),
            ValidationRule(
                name="입행년월이_출생년월보다_이전",
                check=lambda r: (
                    pd.notna(r.get('출생년월')) and
                    pd.notna(r.get('입행년월')) and
                    r.get('입행년월') < r.get('출생년월')
                )
            ),
        ]

        # 검증 제외 조건: 임원실은 검증 제외
        skip_condition = lambda r: r.get('그룹') in Config.VALIDATION_SKIP_GROUPS

        return self._validate_dataframe(df, rules, skip_condition, "직원 데이터")

    def validate_promotion_data(self, df: pd.DataFrame, valid_positions: List[str]) -> pd.DataFrame:
        """승진 데이터 검증 및 오류여부 컬럼 추가

        Args:
            df: 검증할 승진 데이터프레임
            valid_positions: 유효한 승진 직급 목록

        Returns:
            오류여부 컬럼이 추가된 데이터프레임 (오류:1, 정상:0)
        """
        def _normalize_yyyymm(value) -> str:
            """승진년월 값을 정규화 (float → int → str)"""
            if pd.isna(value):
                return ''
            # float(202407.0) → int(202407) → str("202407")
            try:
                return str(int(float(value)))
            except (ValueError, TypeError):
                return str(value)

        def check_promotion_date_format(row):
            """승진년월 형식 검증"""
            승진년월 = _normalize_yyyymm(row.get('승진년월'))
            return len(승진년월) != 6 or not 승진년월.isdigit()

        def check_promotion_date_range(row):
            """승진년월 범위 검증"""
            승진년월 = _normalize_yyyymm(row.get('승진년월'))
            if len(승진년월) != 6 or not 승진년월.isdigit():
                return False  # 이미 형식 오류에서 처리
            try:
                year = int(승진년월[:4])
                month = int(승진년월[4:6])
                return (year < Config.MIN_YEAR or year > Config.MAX_YEAR or
                        month < 1 or month > 12)
            except:
                return False

        def check_invalid_position(row):
            """승진직급 유효성 검증"""
            승진직급 = row.get('승진직급')
            if pd.isna(승진직급) or str(승진직급).strip() == '':
                return False  # 누락 검증에서 처리
            return str(승진직급) not in valid_positions

        rules = [
            ValidationRule(
                name="직번_누락",
                check=lambda r: pd.isna(r.get('직번'))
            ),
            ValidationRule(
                name="이름_누락",
                check=lambda r: pd.isna(r.get('이름')) or str(r.get('이름')).strip() == ''
            ),
            ValidationRule(
                name="승진년월_형식오류",
                check=check_promotion_date_format,
                message=lambda r: f"승진년월_형식오류({r.get('승진년월')})"
            ),
            ValidationRule(
                name="승진년월_범위오류",
                check=check_promotion_date_range,
                message=lambda r: f"승진년월_범위오류({r.get('승진년월')})"
            ),
            ValidationRule(
                name="승진직급_누락",
                check=lambda r: pd.isna(r.get('승진직급')) or str(r.get('승진직급')).strip() == ''
            ),
            ValidationRule(
                name="승진직급_미정의",
                check=check_invalid_position,
                message=lambda r: f"승진직급_미정의({r.get('승진직급')})"
            ),
        ]

        return self._validate_dataframe(df, rules, None, "승진 데이터")

    def validate_ceo_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """CEO 데이터 검증 및 오류여부 컬럼 추가

        Args:
            df: 검증할 CEO 데이터프레임

        Returns:
            오류여부 컬럼이 추가된 데이터프레임 (오류:1, 정상:0)
        """
        rules = [
            ValidationRule(
                name="이름_누락",
                check=lambda r: pd.isna(r.get('이름')) or str(r.get('이름')).strip() == ''
            ),
            ValidationRule(
                name="직위_누락",
                check=lambda r: pd.isna(r.get('직위')) or str(r.get('직위')).strip() == ''
            ),
            ValidationRule(
                name="취임일자_누락",
                check=lambda r: pd.isna(r.get('취임일자'))
            ),
            ValidationRule(
                name="취임년월_변환실패",
                check=lambda r: pd.isna(r.get('취임년월'))
            ),
        ]

        return self._validate_dataframe(df, rules, None, "CEO 데이터")
