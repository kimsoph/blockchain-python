# -*- coding: utf-8 -*-
"""
IBK HR 빌드 커스텀 예외 모듈

계층적 예외 구조로 에러 처리를 체계화합니다.
"""


class HRBuildError(Exception):
    """HR 빌드 기본 예외

    모든 커스텀 예외의 베이스 클래스입니다.
    """

    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self):
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


class DataValidationError(HRBuildError):
    """데이터 검증 실패

    데이터가 예상한 형식이나 범위를 벗어날 때 발생합니다.
    """

    def __init__(self, field: str, value, message: str = None):
        self.field = field
        self.value = value
        msg = message or f"'{field}' 필드 검증 실패: {value}"
        super().__init__(msg, {"field": field, "value": value})


class DateConversionError(HRBuildError):
    """날짜 변환 실패

    날짜 문자열을 파싱하거나 변환할 수 없을 때 발생합니다.
    """

    def __init__(self, date_value, expected_format: str = "YYYYMM"):
        self.date_value = date_value
        self.expected_format = expected_format
        msg = f"날짜 변환 실패: '{date_value}' (기대 형식: {expected_format})"
        super().__init__(msg, {"date_value": date_value, "expected_format": expected_format})


class CSVLoadError(HRBuildError):
    """CSV 파일 로드 실패

    CSV 파일을 찾을 수 없거나 읽을 수 없을 때 발생합니다.
    """

    def __init__(self, file_path: str, reason: str = None):
        self.file_path = file_path
        self.reason = reason
        msg = f"CSV 로드 실패: {file_path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, {"file_path": file_path, "reason": reason})


class ConfigurationError(HRBuildError):
    """설정 오류

    필수 설정값이 누락되거나 잘못된 경우 발생합니다.
    """

    def __init__(self, config_key: str, message: str = None):
        self.config_key = config_key
        msg = message or f"설정 오류: {config_key}"
        super().__init__(msg, {"config_key": config_key})
