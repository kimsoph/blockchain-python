# -*- coding: utf-8 -*-
"""
승진 데이터 처리 모듈

ibk_pmt.csv를 읽어서 승진 정보를 가공합니다.
"""

import pandas as pd
import logging
from typing import Optional, Tuple

from core.config import Config
from core.utils import calculate_interval_years, calculate_years
from core.validators import DataValidator
from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class PromotionProcessor(BaseProcessor):
    """승진 데이터 처리 클래스"""

    @property
    def csv_filename(self) -> str:
        return Config.PROMOTION_RAW_FILE

    @property
    def data_type_name(self) -> str:
        return "승진 데이터"

    def process(self, df_employee: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """승진 데이터 처리 메인 메서드

        Args:
            df_employee: 직원 데이터프레임 (입행년월 정보 활용)

        Returns:
            Tuple[승진 목록 데이터프레임, 승진 이력 데이터프레임]
        """
        self._log_start()

        df = self._load_data()
        promotion_list = self._parse_promotions(df)
        df_promotion = pd.DataFrame(promotion_list)

        # 검증
        df_promotion = self.validator.validate_promotion_data(
            df_promotion,
            Config.PROMOTION_ORDER
        )

        # 중복 제거 및 정렬
        df_promotion = df_promotion.drop_duplicates().sort_values(['직번', '승진년월'])

        # 승진 간격 계산
        df_promotion = self._calculate_intervals(df_promotion)

        # 입행년월 정보로 첫 승진까지 소요기간 계산
        if df_employee is not None:
            df_promotion = self._add_first_promotion_interval(df_promotion, df_employee)

        # 승진 이력 (경로) 생성
        df_history = self._create_promotion_history(df_promotion)

        logger.info(f"{self.data_type_name} 처리 완료: {len(df_promotion)}건 (이력: {len(df_history)}명)")

        return df_promotion, df_history

    def _parse_promotions(self, df: pd.DataFrame) -> list:
        """승진 정보 파싱 (벡터화 방식)

        CSV 형식: 직번, 이름, 승진부점, 컬럼1, 컬럼2, ...
        각 컬럼의 값: "YYYYMM_승진직급" 형식
        """
        # 고정 컬럼과 승진 정보 컬럼 분리
        fixed_cols = ['직번', '이름', '승진부점']
        value_cols = [col for col in df.columns if col not in fixed_cols and col != '']

        if not value_cols:
            return []

        # melt로 wide → long 변환
        df_melted = df.melt(
            id_vars=fixed_cols,
            value_vars=value_cols,
            var_name='컬럼명',
            value_name='승진정보'
        )

        # 빈 값 제거
        df_melted = df_melted[
            df_melted['승진정보'].notna() &
            (df_melted['승진정보'].astype(str).str.strip() != '')
        ].copy()

        if df_melted.empty:
            return []

        # 승진정보 파싱 (YYYYMM_승진직급)
        def parse_info(info):
            parts = str(info).split('_')
            if len(parts) == 2:
                # 승진년월을 INTEGER로 변환 (스키마와 일치)
                승진년월 = int(parts[0]) if parts[0].isdigit() else parts[0]
                return pd.Series({'승진년월': 승진년월, '승진직급': parts[1]})
            return pd.Series({'승진년월': None, '승진직급': None})

        parsed = df_melted['승진정보'].apply(parse_info)
        df_melted = pd.concat([df_melted, parsed], axis=1)

        # 유효한 파싱 결과만 필터링
        df_melted = df_melted[df_melted['승진년월'].notna()]

        # 결과를 dict 리스트로 변환
        promotion_list = df_melted[['직번', '이름', '승진직급', '승진년월', '승진부점']].copy()
        promotion_list['소요기간'] = None

        return promotion_list.to_dict('records')

    def _calculate_intervals(self, df: pd.DataFrame) -> pd.DataFrame:
        """각 직원별로 승진 간격 계산"""
        def calculate_group_intervals(group):
            group = group.sort_values('승진년월')
            intervals = []

            for i in range(len(group)):
                if i == 0:
                    intervals.append(None)
                else:
                    prev_date = str(group.iloc[i-1]['승진년월'])
                    curr_date = str(group.iloc[i]['승진년월'])
                    interval = calculate_interval_years(prev_date, curr_date)
                    intervals.append(interval)

            group['소요기간'] = intervals
            return group

        return df.groupby('직번', group_keys=False).apply(calculate_group_intervals)

    def _add_first_promotion_interval(self, df_promotion: pd.DataFrame,
                                      df_employee: pd.DataFrame) -> pd.DataFrame:
        """입행년월 정보를 활용한 첫 승진까지 소요기간 계산"""
        employee_info = df_employee[['직번', '입행년월']].drop_duplicates()
        employee_info['직번'] = employee_info['직번'].astype(int)

        df_promotion = df_promotion.merge(employee_info, on='직번', how='left')

        first_promotions = df_promotion.groupby('직번').first().reset_index()

        def calculate_first_interval(row):
            if pd.notna(row['입행년월']) and pd.notna(row['승진년월']):
                return calculate_interval_years(
                    int(row['입행년월']),
                    row['승진년월']
                )
            return None

        first_promotions['첫승진소요'] = first_promotions.apply(
            calculate_first_interval, axis=1
        )

        df_promotion = df_promotion.merge(
            first_promotions[['직번', '첫승진소요']],
            on='직번',
            how='left'
        )

        # 각 직원의 첫 번째 승진에만 소요기간 적용
        mask = df_promotion.groupby('직번').cumcount() == 0
        df_promotion.loc[mask, '소요기간'] = df_promotion.loc[mask, '첫승진소요']

        # 임시 컬럼 제거
        df_promotion = df_promotion.drop(['입행년월', '첫승진소요'], axis=1)

        return df_promotion

    def _create_promotion_history(self, df_promotion: pd.DataFrame) -> pd.DataFrame:
        """승진 이력 (경로) 데이터프레임 생성

        각 직원의 승진 경로를 "승0←승1←승2" 형식으로 집계
        """
        # 마지막 승진 정보 추출
        last_promotion = df_promotion.sort_values(['직번', '승진년월']).groupby('직번').last()

        # 경로 집계
        df_history = df_promotion.groupby('직번').agg({
            '이름': 'first',
            '승진직급': lambda x: '←'.join(x.astype(str)[::-1]),
            '소요기간': lambda x: '←'.join(x.fillna('').astype(str)[::-1]),
            '승진부점': lambda x: '←'.join(x.fillna('')[::-1])
        }).reset_index()

        # 컬럼명 변경
        df_history.columns = ['직번', '이름', '승진경로', '소요기간경로', '승진부점경로']

        # 마지막 승진직급과 직급연차 추가
        df_history['승진직급'] = df_history['직번'].map(last_promotion['승진직급'])
        df_history['직급연차'] = df_history['직번'].map(
            last_promotion['승진년월'].apply(
                lambda x: calculate_years(x, self.config.reference_date) if pd.notna(x) else None
            )
        )

        return df_history
