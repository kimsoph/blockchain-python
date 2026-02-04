# -*- coding: utf-8 -*-
"""
직원 데이터 처리 모듈

ibk_man.csv를 읽어서 직원 정보를 가공합니다.
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

from core.config import Config
from core.utils import (
    calculate_age,
    calculate_years,
    date_to_yyyymm,
    convert_birth_date,
    calculate_impi_date
)
from core.validators import DataValidator
from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class EmployeeProcessor(BaseProcessor):
    """직원 데이터 처리 클래스"""

    @property
    def csv_filename(self) -> str:
        return Config.EMPLOYEE_RAW_FILE

    @property
    def data_type_name(self) -> str:
        return "직원 데이터"

    def process(self) -> pd.DataFrame:
        """직원 데이터 처리 메인 메서드

        Returns:
            처리된 직원 데이터프레임
        """
        self._log_start()

        df = self._load_data()
        df = self._rename_columns(df)
        df = self._convert_dates(df)
        df = self._calculate_ages_and_years(df)
        df = self._set_levels(df)
        df = self._classify_departments(df)
        df = self._set_boolean_fields(df)
        df = self._calculate_ranking(df)
        df = self._update_groups(df)
        df = self.validator.validate_employee_data(df)
        df = self._reorder_columns(df)

        self._log_complete(df)
        return df

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """컬럼명 변경"""
        return df.rename(columns=Config.COLUMN_MAPPING)

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """날짜 형식 변환"""
        # 축약된 출생년월을 전체 연도로 변환 (실제생년월일 참고)
        df['출생년월'] = df.apply(
            lambda row: convert_birth_date(
                row['출생년월'],
                self.config.reference_date,
                row.get('실제생년월일')
            ),
            axis=1
        )
        df['입행년월'] = df['입행년월'].apply(date_to_yyyymm)
        df['소속년월'] = df['소속년월'].apply(date_to_yyyymm)
        df['직위년월'] = df['직위년월'].apply(date_to_yyyymm)
        return df

    def _calculate_ages_and_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """나이 및 연차 계산"""
        ref_date = self.config.reference_date

        df['현재나이'] = df['출생년월'].apply(
            lambda x: calculate_age(x, ref_date)
        )
        df['입행연차'] = df['입행년월'].apply(
            lambda x: calculate_years(x, ref_date)
        )
        df['소속연차'] = df['소속년월'].apply(
            lambda x: calculate_years(x, ref_date)
        )
        df['입행나이'] = df.apply(
            lambda row: calculate_age(row['출생년월'], row['입행년월']),
            axis=1
        )
        df['임피년월'] = df['출생년월'].apply(calculate_impi_date)

        return df

    def _set_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """레벨 설정"""
        # 특수 케이스 처리
        df.loc[(df['직급'] == 0) & (df['직위'] == '0'), '직위'] = '용역'
        df.loc[(df['직급'] == 0) & (~df['직위'].isin(['용역', '은행장', '전무이사', '감사', '사외이사'])), '직위'] = '준정'
        df.loc[df['호칭'].str.contains('고경력', na=False), '직위'] = '고경력'
        df.loc[df['직위'].str.contains('집행간부', na=False), '직위'] = '집행간부'

        # 레벨 매핑
        df['레벨'] = df['직위'].replace(Config.LEVEL_MAPPING, regex=False)

        # 부점장 레벨에 직급 숫자 추가 (부점장1, 부점장2, 부점장3)
        df['레벨'] = df.apply(
            lambda row: f"{row['레벨']}{row['직급']}" if row['레벨'] == '부점장' else row['레벨'],
            axis=1
        )

        return df

    def _classify_departments(self, df: pd.DataFrame) -> pd.DataFrame:
        """부서 분류

        Note:
            - 일반 문자열 매핑: '일반영업점', '지역본부', '본부영업점'
            - 정규식 매핑: '^본부.*치$' (본부로 시작하고 치로 끝남)
            - replace(regex=True)로 일괄 처리
        """
        dept_mapping = {
            # 일반 문자열 매핑
            '일반영업점': '지점',
            '지역본부': '지본',
            '본부영업점': '본영',
            # 정규식 매핑 (본부*치 패턴)
            '^본부.*치$': '본점'
        }
        df['세분'] = df['부점구분'].replace(dept_mapping, regex=True)

        # 해외 파견자 처리
        df.loc[
            df['부점'].str.contains('글로벌영업지원', na=False) &
            df['호칭'].str.contains('조사역', na=False),
            '세분'
        ] = '해외'

        return df

    def _set_boolean_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Boolean 필드 설정 (1: True, 0: False)"""
        df['본점여부'] = (df['세분'] == '본점').astype(int)
        df['남성여부'] = (df['성별'] == 'M').astype(int)

        # 인원 포함 여부 (노동조합, 파견, 고경력 등 제외)
        # 대기(?!업): 순수 "대기"만 매칭, "대기업금융팀장" 등 정상 직책은 제외
        df['인원포함여부'] = (~(
            (df['팀명'].str.contains('기타$|노동조합|파견$', na=False)) |
            (df['호칭'].str.contains(r'고경력|대기(?!업)|후선|인턴', na=False))
        )).astype(int)

        # 승진 대상 여부 (인원포함여부와 독립 — 노동조합/파견은 승진대상 가능)
        # *기타 팀(인사부기타 등 대기/휴직 포함)과 대기 호칭은 제외
        df['승진대상여부'] = (
            (df['레벨'] != '기타') &
            (~df['팀명'].str.contains('기타$', na=False)) &
            (~df['호칭'].str.contains(r'대기(?!업)', na=False))
        ).astype(int)

        return df

    def _calculate_ranking(self, df: pd.DataFrame) -> pd.DataFrame:
        """랭킹 계산"""
        df['랭킹'] = np.where(
            (df['승진대상여부'] == 1) & df['서열'].notna(),
            df['서열'].rank(method='min'),
            999999
        ).astype(int)

        return df

    def _update_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """그룹 업데이트 (조직 개편 반영)"""
        df['그룹'] = df['그룹'].replace(Config.GROUP_MAPPING)
        return df

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """컬럼 순서 정리"""
        all_columns = (
            Config.STANDARD_COLUMNS +
            ['직위년월', '실제생년월일', '양력환산생년월일', '기타업무내용',
             '현재나이', '입행연차', '소속연차', '입행나이', '임피년월',
             '레벨', '세분', '본점여부', '남성여부', '인원포함여부',
             '승진대상여부', '랭킹', '오류여부', '오류사유']
        )

        # 존재하는 컬럼만 선택
        existing_columns = [col for col in all_columns if col in df.columns]
        return df[existing_columns]
