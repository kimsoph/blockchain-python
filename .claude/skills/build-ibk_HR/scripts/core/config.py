# -*- coding: utf-8 -*-
"""
IBK HR 데이터 처리를 위한 설정 모듈

컬럼 매핑, 레벨 체계, 경로 설정을 관리합니다.
"""

from pathlib import Path
from typing import Dict, List


class Config:
    """설정 클래스 - 인스턴스 기반으로 경로 및 기준년월 관리"""

    # 기본 경로 (볼트 기준)
    DEFAULT_CSV_DIR = Path("3_Resources/R-about_ibk/sources/csv-ibk_HR")
    DEFAULT_OUTPUT_DIR = Path("3_Resources/R-DB")
    DEFAULT_ARCHIVE_DIR = Path("4_Archive/Resources/R-about_ibk")
    DEFAULT_DB_NAME = "ibk_HR.db"

    ENCODING = "utf-8-sig"

    # === 검증 상수 ===
    # 나이 범위
    MIN_AGE = 16
    MAX_AGE = 80
    MAX_JOIN_AGE = 70  # 최대 입행 나이

    # 연도 범위
    MIN_YEAR = 1960
    MAX_YEAR = 2030

    # 출생년월 변환 경계 (30 미만 -> 2000년대, 30 이상 -> 1900년대)
    CENTURY_BOUNDARY = 30

    # 제외 대상 패턴 (정규식)
    EXCLUDE_TEAM_PATTERN = r'기타$|노동조합|파견$'
    EXCLUDE_TITLE_PATTERN = r'고경력|대기(?!업)|후선|인턴'

    # 검증 제외 그룹
    VALIDATION_SKIP_GROUPS = ['임원실']

    # 컬럼명 매핑 (원본 → 표준)
    COLUMN_MAPPING = {
        '직원번호': '직번', '직원명': '이름', '직급코드': '직급',
        '인사직위명': '직위', '소속그룹코드': '그룹코드', '소속그룹명': '그룹',
        '소속부점코드': '부점코드', '소속부점명': '부점', '소속팀코드': '팀코드',
        '소속팀명': '팀명', '대외호칭명': '호칭', '직원명부순서': '서열',
        '현소속년월일': '소속년월'
    }

    # 직위 → 레벨 매핑
    LEVEL_MAPPING = {
        '은행장': '임원', '전무이사': '임원', '감사': '임원', '사외이사': '임원',
        '집행간부': '부행장', '본부장': '본부장',
        '부장': '부점장', '지점장': '부점장', '부점장급': '부점장',
        '부부장': '팀장', '부지점장': '팀장', '부부점장급': '팀장',
        '차장': '책임자', '과장': '책임자',
        '대리': '행원', '계장': '행원',
        '준정': '기타', '용역': '기타', '고경력': '기타'
    }

    # 레벨 순서 (정렬용)
    LEVEL_ORDER = [
        '임원', '부행장', '본부장',
        '부점장1', '부점장2', '부점장3',
        '팀장', '책임자', '행원', '기타'
    ]

    # 승진 직급 순서
    PROMOTION_ORDER = ['승0', '승1', '승2', 'PCEO', '승3', '승4', '입행']

    # 승진기준년수 (현재 직급 → 최소 직급연차)
    PROMOTION_TENURE_REQUIREMENTS = {
        '승4': 9.0,
        '승3': 6.0,
        'PCEO': 3.0,
        '승2': 1.0,
        '승1': 0.5,
    }

    # 그룹 매핑 (조직 개편 반영)
    GROUP_MAPPING = {
        '데이터본부': '디지털그룹',
        'IT개발본부': 'IT그룹',
        'IT운영본부': 'IT그룹'
    }

    # 직원 데이터 표준 컬럼
    STANDARD_COLUMNS = [
        '직번', '이름', '성별', '출생년월', '입행년월', '직급',
        '직위코드', '직위', '그룹코드', '그룹', '부점코드', '부점',
        '팀코드', '팀명', '호칭', '부점구분', '서열', '소속년월', '보임코드'
    ]

    # CSV 파일명
    EMPLOYEE_RAW_FILE = "ibk_man.csv"
    PROMOTION_RAW_FILE = "ibk_pmt.csv"
    CEO_RAW_FILE = "ibk_ceo.csv"

    def __init__(self,
                 csv_dir: Path = None,
                 output_dir: Path = None,
                 archive_dir: Path = None,
                 db_name: str = None,
                 reference_date: int = 202601):
        """
        Config 인스턴스 초기화

        Args:
            csv_dir: CSV 파일들이 있는 디렉토리
            output_dir: 출력 파일을 저장할 디렉토리
            archive_dir: 백업 파일을 저장할 아카이브 디렉토리
            db_name: 생성할 DB 파일명
            reference_date: 기준년월 (YYYYMM 형식)
        """
        self.csv_dir = csv_dir or self.DEFAULT_CSV_DIR
        self.output_dir = output_dir or self.DEFAULT_OUTPUT_DIR
        self.archive_dir = archive_dir or self.DEFAULT_ARCHIVE_DIR
        self.db_name = db_name or self.DEFAULT_DB_NAME
        self.reference_date = reference_date

    @property
    def db_path(self) -> Path:
        """DB 파일 전체 경로"""
        return self.output_dir / self.db_name

    def get_archive_path(self, build_date: str = None) -> Path:
        """아카이브 DB 파일 경로 생성

        Args:
            build_date: 빌드 날짜 (YYYYMMDD 형식). None이면 오늘 날짜 사용

        Returns:
            아카이브 파일 경로 (예: 4_Archive/Resources/R-about_ibk/ibk_HR_202601_20260116.db)
        """
        from datetime import datetime
        if build_date is None:
            build_date = datetime.now().strftime('%Y%m%d')
        stem = self.db_name.replace('.db', '')
        return self.archive_dir / f"{stem}_{self.reference_date}_{build_date}.db"

    def get_csv_path(self, filename: str) -> Path:
        """CSV 파일 전체 경로 반환"""
        return self.csv_dir / filename

    def __repr__(self) -> str:
        return (f"Config(csv_dir={self.csv_dir}, "
                f"output_dir={self.output_dir}, "
                f"db_name={self.db_name}, "
                f"reference_date={self.reference_date})")
