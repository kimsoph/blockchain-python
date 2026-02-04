# -*- coding: utf-8 -*-
"""
CEO 데이터 처리 모듈

ibk_ceo.csv를 읽어서 CEO 정보를 가공합니다.
"""

import pandas as pd
import logging

from core.config import Config
from core.utils import date_to_yyyymm
from core.validators import DataValidator
from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class CEOProcessor(BaseProcessor):
    """CEO 데이터 처리 클래스"""

    @property
    def csv_filename(self) -> str:
        return Config.CEO_RAW_FILE

    @property
    def data_type_name(self) -> str:
        return "CEO 데이터"

    def process(self) -> pd.DataFrame:
        """CEO 데이터 처리 메인 메서드

        Returns:
            처리된 CEO 데이터프레임
        """
        self._log_start()

        df = self._load_data()
        df = self._convert_dates(df)
        df = self.validator.validate_ceo_data(df)
        df = self._reorder_columns(df)

        self._log_complete(df)
        return df

    def _convert_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """취임일자를 YYYYMM 형식으로 변환"""
        df['취임년월'] = df['취임일자'].apply(date_to_yyyymm)
        return df

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """컬럼 순서 정리"""
        columns = ['직위', '기수', '이름', '취임일자', '취임년월', '오류여부', '오류사유']
        existing_columns = [col for col in columns if col in df.columns]
        return df[existing_columns]
