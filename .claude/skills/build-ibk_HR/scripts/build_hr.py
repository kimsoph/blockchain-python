#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-ibk_HR: IBK 인사 CSV 데이터를 SQLite DB로 변환

Usage:
    # 기본 빌드 (기준년월 필수)
    python build_hr.py build 202601

    # 사용자 지정 경로
    python build_hr.py build 202601 --csv-dir "path/to/csv" --output "path/to/output.db"

    # 강제 재생성
    python build_hr.py build 202601 --force

    # DB 정보 조회
    python build_hr.py info

    # 데이터 검증
    python build_hr.py verify
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import warnings

# Windows 환경에서 UTF-8 출력 보장
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

warnings.filterwarnings('ignore')

# 스크립트 디렉토리를 path에 추가 (패키지 import를 위해)
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# 모듈 직접 import (상대 import 문제 회피)
from core.config import Config
from core.utils import (
    calculate_age,
    calculate_years,
    calculate_interval_years,
    date_to_yyyymm,
    convert_birth_date,
    calculate_impi_date
)
from core.validators import DataValidator
from db.schema import (
    SCHEMA_VERSION,
    HR_SCHEMA,
    PROMOTION_SCHEMA,
    HR_INDEXES,
    PROMOTION_INDEXES
)
from db.writer import DatabaseWriter, verify_database
from processors.employee_processor import EmployeeProcessor
from processors.promotion_processor import PromotionProcessor
from processors.ceo_processor import CEOProcessor


def setup_logging(verbose: bool = False) -> None:
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s' if verbose else '%(levelname)s: %(message)s'

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def validate_reference_date(date_str: str) -> int:
    """기준년월 유효성 검사"""
    if len(date_str) != 6 or not date_str.isdigit():
        raise argparse.ArgumentTypeError(
            f"잘못된 형식: {date_str}. YYYYMM 형식이어야 합니다 (예: 202601)"
        )

    year = int(date_str[:4])
    month = int(date_str[4:6])

    if year < 2000 or year > 2100:
        raise argparse.ArgumentTypeError(f"연도 범위 오류: {year} (2000~2100)")

    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError(f"월 범위 오류: {month} (1~12)")

    return int(date_str)


def cmd_build(args) -> int:
    """build 명령 실행"""
    logger = logging.getLogger(__name__)

    # 경로 설정
    vault_root = Path.cwd()

    csv_dir = Path(args.csv_dir) if args.csv_dir else vault_root / Config.DEFAULT_CSV_DIR
    output_dir = Path(args.output).parent if args.output else vault_root / Config.DEFAULT_OUTPUT_DIR
    db_name = Path(args.output).name if args.output else Config.DEFAULT_DB_NAME

    # Config 인스턴스 생성
    config = Config(
        csv_dir=csv_dir,
        output_dir=output_dir,
        db_name=db_name,
        reference_date=args.reference_date
    )

    logger.info("=" * 60)
    logger.info("IBK HR 데이터베이스 빌드")
    logger.info("=" * 60)
    logger.info(f"기준년월: {config.reference_date}")
    logger.info(f"CSV 경로: {config.csv_dir}")
    logger.info(f"출력 경로: {config.db_path}")
    logger.info("-" * 60)

    # CSV 파일 존재 확인
    required_files = [
        Config.EMPLOYEE_RAW_FILE,
        Config.PROMOTION_RAW_FILE,
        Config.CEO_RAW_FILE
    ]

    missing_files = []
    for filename in required_files:
        filepath = config.get_csv_path(filename)
        if not filepath.exists():
            missing_files.append(filename)

    if missing_files:
        logger.error(f"필수 CSV 파일이 없습니다:")
        for f in missing_files:
            logger.error(f"  - {f}")
        logger.error(f"경로: {config.csv_dir}")
        return 1

    try:
        # 1. 직원 데이터 처리
        logger.info("[1/4] 직원 데이터 처리 중...")
        employee_processor = EmployeeProcessor(config)
        df_employee = employee_processor.process()
        logger.info(f"  → 완료: {len(df_employee)}명")

        # 2. 승진 데이터 처리
        logger.info("[2/4] 승진 데이터 처리 중...")
        promotion_processor = PromotionProcessor(config)
        df_promotion, df_history = promotion_processor.process(df_employee)
        logger.info(f"  → 완료: {len(df_promotion)}건 (이력: {len(df_history)}명)")

        # 3. HR 데이터 통합 (employee + promotion history)
        logger.info("[3/4] HR 데이터 통합 중...")
        df_hr = _merge_hr_data(df_employee, df_history)
        logger.info(f"  → 완료: {len(df_hr)}명, {len(df_hr.columns)}컬럼")

        # 4. DB 저장
        logger.info("[4/4] 데이터베이스 저장 중...")
        writer = DatabaseWriter(config)
        result = writer.save(df_hr, df_promotion, force=args.force)

        if result['status'] == 'success':
            logger.info("=" * 60)
            logger.info("빌드 완료!")
            logger.info(f"  - DB 경로: {result['db_path']}")
            logger.info(f"  - HR 테이블: {result['hr_count']}행")
            logger.info(f"  - promotion_list 테이블: {result['promotion_count']}행")
            if result['archived']:
                logger.info(f"  - 아카이브: {result['archive_path']}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error(f"저장 실패: {result.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        logger.error(f"빌드 실패: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _merge_hr_data(df_employee, df_history):
    """직원 데이터와 승진 이력 병합"""
    import pandas as pd

    history_columns = ['직번', '승진경로', '소요기간경로', '승진부점경로', '승진직급', '직급연차']
    existing_history_cols = [col for col in history_columns if col in df_history.columns]

    df_hr = pd.merge(
        df_employee,
        df_history[existing_history_cols],
        on='직번',
        how='left'
    )

    # 승진대상여부 재계산 (직급연차 기반)
    # 기본 조건(인원포함여부=1 AND 레벨≠기타)은 이미 df_employee에서 설정됨
    # 승진직급별 기준년수를 충족하는지 추가 검증
    for grade, min_tenure in Config.PROMOTION_TENURE_REQUIREMENTS.items():
        mask = (df_hr['승진직급'] == grade)
        df_hr.loc[mask, '승진대상여부'] = (
            (df_hr.loc[mask, '승진대상여부'] == 1) &
            (df_hr.loc[mask, '직급연차'].fillna(0) >= min_tenure)
        ).astype(int)

    # 승0은 최상위이므로 승진 대상 아님
    df_hr.loc[df_hr['승진직급'] == '승0', '승진대상여부'] = 0

    # 승진직급 NULL(승진 이력 없음) + 행원은 승진 대상 아님
    df_hr.loc[df_hr['승진직급'].isna() & (df_hr['레벨'] == '행원'), '승진대상여부'] = 0

    # 컬럼 순서 정리
    hr_columns = [
        '직번', '이름', '성별', '직급', '직위', '레벨', '승진직급', '직급연차',
        '그룹', '부점', '팀명', '서열', '랭킹', '출생년월', '입행년월',
        '현재나이', '입행연차', '입행나이', '임피년월', '승진경로', '소요기간경로',
        '승진부점경로', '세분', '본점여부', '남성여부', '인원포함여부', '승진대상여부',
        '실제생년월일', '직위년월', '소속년월', '소속연차', '오류여부', '오류사유'
    ]

    existing_columns = [col for col in hr_columns if col in df_hr.columns]
    return df_hr[existing_columns]


def cmd_info(args) -> int:
    """info 명령 실행"""
    logger = logging.getLogger(__name__)

    vault_root = Path.cwd()
    db_path = Path(args.db) if args.db else vault_root / Config.DEFAULT_OUTPUT_DIR / Config.DEFAULT_DB_NAME

    if not db_path.exists():
        logger.error(f"DB 파일이 없습니다: {db_path}")
        return 1

    result = verify_database(db_path)

    print("\n" + "=" * 60)
    print("IBK HR 데이터베이스 정보")
    print("=" * 60)
    print(f"경로: {db_path}")
    print(f"상태: {'정상' if result['valid'] else '오류'}")

    if result.get('metadata'):
        print("\n[메타데이터]")
        for key, value in result['metadata'].items():
            print(f"  - {key}: {value}")

    print("\n[테이블]")
    for table, info in result['tables'].items():
        if info['exists']:
            print(f"  - {table}: {info['row_count']:,}행")
        else:
            print(f"  - {table}: (없음)")

    if result['errors']:
        print("\n[오류]")
        for error in result['errors']:
            print(f"  - {error}")

    print("=" * 60 + "\n")

    return 0 if result['valid'] else 1


def cmd_verify(args) -> int:
    """verify 명령 실행"""
    logger = logging.getLogger(__name__)

    vault_root = Path.cwd()
    db_path = Path(args.db) if args.db else vault_root / Config.DEFAULT_OUTPUT_DIR / Config.DEFAULT_DB_NAME

    if not db_path.exists():
        logger.error(f"DB 파일이 없습니다: {db_path}")
        return 1

    result = verify_database(db_path)

    if result['valid']:
        logger.info(f"검증 성공: {db_path}")
        for table, info in result['tables'].items():
            logger.info(f"  - {table}: {info['row_count']:,}행")
        return 0
    else:
        logger.error("검증 실패:")
        for error in result['errors']:
            logger.error(f"  - {error}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='IBK 인사 CSV 데이터를 SQLite DB로 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python build_hr.py build 202601                    # 기본 빌드
  python build_hr.py build 202507 --force            # 강제 재생성
  python build_hr.py build 202601 --csv-dir ./CSV    # 사용자 경로
  python build_hr.py info                            # DB 정보 조회
  python build_hr.py verify                          # 데이터 검증
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='상세 로그 출력')
    parser.add_argument('--version', action='version', version='build-ibk_HR v1.0.0')

    subparsers = parser.add_subparsers(dest='command', help='명령어')

    # build 명령
    build_parser = subparsers.add_parser('build', help='DB 생성/업데이트')
    build_parser.add_argument('reference_date', type=validate_reference_date,
                              help='기준년월 (YYYYMM 형식, 예: 202601)')
    build_parser.add_argument('--csv-dir', type=str,
                              help='CSV 파일 디렉토리 (기본: 3_Resources/R-about_ibk/sources/csv-ibk_HR)')
    build_parser.add_argument('--output', '-o', type=str,
                              help='출력 DB 파일 경로 (기본: 3_Resources/R-about_ibk/outputs/ibk_HR.db)')
    build_parser.add_argument('--force', '-f', action='store_true',
                              help='강제 재생성')
    build_parser.set_defaults(func=cmd_build)

    # info 명령
    info_parser = subparsers.add_parser('info', help='DB 정보 조회')
    info_parser.add_argument('--db', type=str,
                             help='DB 파일 경로')
    info_parser.set_defaults(func=cmd_info)

    # verify 명령
    verify_parser = subparsers.add_parser('verify', help='데이터 검증')
    verify_parser.add_argument('--db', type=str,
                               help='DB 파일 경로')
    verify_parser.set_defaults(func=cmd_verify)

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
