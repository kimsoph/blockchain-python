# -*- coding: utf-8 -*-
"""
프로세서 베이스 클래스 모듈

모든 데이터 프로세서가 상속하는 추상 기본 클래스입니다.
공통 로직을 중앙화하여 코드 중복을 제거하고 테스트 가능성을 높입니다.
"""

from abc import ABC, abstractmethod
import pandas as pd
import logging
from pathlib import Path
from typing import Optional

from core.config import Config
from core.validators import DataValidator
from core.exceptions import CSVLoadError

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """프로세서 추상 기본 클래스

    모든 데이터 프로세서가 상속하는 기본 클래스입니다.
    공통 기능을 제공하고 일관된 인터페이스를 강제합니다.

    Attributes:
        config: Config 인스턴스
        validator: DataValidator 인스턴스 (DI 지원)
    """

    def __init__(self, config: Config, validator: DataValidator = None):
        """
        Args:
            config: Config 인스턴스
            validator: DataValidator 인스턴스 (기본값: 새 인스턴스 생성)
                       테스트 시 Mock 객체 주입 가능
        """
        self.config = config
        self.validator = validator or DataValidator()

    @property
    @abstractmethod
    def csv_filename(self) -> str:
        """처리할 CSV 파일명

        Returns:
            CSV 파일명 (예: "ibk_man.csv")
        """
        pass

    @property
    @abstractmethod
    def data_type_name(self) -> str:
        """데이터 타입 이름 (로깅용)

        Returns:
            데이터 타입명 (예: "직원 데이터")
        """
        pass

    def _get_csv_path(self) -> Path:
        """CSV 파일 경로 반환"""
        return self.config.get_csv_path(self.csv_filename)

    def _load_data(self) -> pd.DataFrame:
        """CSV 파일 로드

        Returns:
            로드된 데이터프레임

        Raises:
            CSVLoadError: 파일이 없거나 읽을 수 없는 경우
        """
        file_path = self._get_csv_path()
        logger.debug(f"Loading {self.data_type_name} from {file_path}")

        if not file_path.exists():
            raise CSVLoadError(str(file_path), "파일이 존재하지 않습니다")

        try:
            return pd.read_csv(file_path, encoding=Config.ENCODING)
        except Exception as e:
            raise CSVLoadError(str(file_path), str(e))

    @abstractmethod
    def process(self) -> pd.DataFrame:
        """데이터 처리 메인 메서드

        서브클래스에서 구현해야 합니다.

        Returns:
            처리된 데이터프레임
        """
        pass

    def _log_start(self) -> None:
        """처리 시작 로그"""
        logger.info(f"{self.data_type_name} 처리 시작")

    def _log_complete(self, df: pd.DataFrame) -> None:
        """처리 완료 로그"""
        logger.info(f"{self.data_type_name} 처리 완료: {len(df)}행")
