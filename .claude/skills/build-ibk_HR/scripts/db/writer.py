# -*- coding: utf-8 -*-
"""
IBK HR DB 저장 모듈

HR 데이터를 SQLite DB로 저장하고 관리합니다.
"""

import sqlite3
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, Optional

from core.config import Config
from db.schema import (
    SCHEMA_VERSION,
    HR_SCHEMA,
    PROMOTION_SCHEMA,
    HR_INDEXES,
    PROMOTION_INDEXES
)

logger = logging.getLogger(__name__)


def _schema_to_dtype(schema: dict) -> dict:
    """스키마 정의를 pandas to_sql용 dtype으로 변환

    Args:
        schema: 스키마 딕셔너리 (HR_SCHEMA 또는 PROMOTION_SCHEMA)

    Returns:
        {컬럼명: SQLite 타입} 딕셔너리
    """
    return {col['name']: col['type'] for col in schema['columns']}


class DatabaseWriter:
    """SQLite DB 저장 클래스"""

    def __init__(self, config: Config):
        """
        Args:
            config: Config 인스턴스
        """
        self.config = config
        self.db_path = config.db_path

    def save(self, df_hr: pd.DataFrame, df_promotion: pd.DataFrame,
             force: bool = False) -> Dict[str, Any]:
        """HR 데이터와 승진 데이터를 DB로 저장

        Args:
            df_hr: HR 데이터프레임
            df_promotion: 승진 데이터프레임
            force: 강제 재생성 여부

        Returns:
            저장 결과 정보
        """
        result = {
            'status': 'success',
            'db_path': str(self.db_path),
            'hr_count': 0,
            'promotion_count': 0,
            'archived': False,
            'archive_path': None,
            'created_at': datetime.now().isoformat()
        }

        try:
            # 출력 디렉토리 확인
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # 기존 DB 아카이빙 (force=True 시 스킵)
            if self.db_path.exists():
                if force:
                    logger.info("강제 재생성 모드: 기존 DB 아카이빙 생략")
                    result['archived'] = False
                else:
                    archive_path = self._archive_database()
                    if archive_path:
                        result['archived'] = True
                        result['archive_path'] = str(archive_path)

            # 임시 DB 파일에 저장
            temp_db_path = self.db_path.with_suffix('.tmp.db')
            conn = sqlite3.connect(temp_db_path)

            try:
                # 스키마 기반 dtype 매핑
                hr_dtype = _schema_to_dtype(HR_SCHEMA)
                promotion_dtype = _schema_to_dtype(PROMOTION_SCHEMA)

                # HR 테이블 저장 (dtype 명시)
                df_hr.to_sql('HR', conn, if_exists='replace', index=False, dtype=hr_dtype)
                result['hr_count'] = len(df_hr)
                logger.info(f"HR 테이블 저장 완료: {len(df_hr)}행")

                # promotion_list 테이블 저장 (dtype 명시)
                df_promotion.to_sql('promotion_list', conn, if_exists='replace', index=False, dtype=promotion_dtype)
                result['promotion_count'] = len(df_promotion)
                logger.info(f"promotion_list 테이블 저장 완료: {len(df_promotion)}행")

                # 인덱스 생성
                self._create_indexes(conn)

                # 메타데이터 테이블 생성
                self._create_metadata_table(conn)

                conn.commit()

            finally:
                conn.close()

            # 임시 파일을 실제 파일로 이동
            if temp_db_path.exists():
                if self.db_path.exists():
                    self.db_path.unlink()
                shutil.move(str(temp_db_path), str(self.db_path))

            logger.info(f"데이터베이스 저장 완료: {self.db_path}")

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"데이터베이스 저장 실패: {e}")

            # 임시 파일 정리
            temp_db_path = self.db_path.with_suffix('.tmp.db')
            if temp_db_path.exists():
                temp_db_path.unlink()

            raise

        return result

    def _archive_database(self) -> Optional[Path]:
        """기존 DB를 아카이브 폴더로 이동

        Returns:
            아카이브 파일 경로 (예: 4_Archive/Resources/R-about_ibk/ibk_HR_202601_20260116.db)
        """
        if not self.db_path.exists():
            return None

        # 기존 DB의 기준년월 읽기
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM _metadata WHERE key = 'reference_date'")
            row = cursor.fetchone()
            old_reference_date = row[0] if row else str(self.config.reference_date)
            conn.close()
        except Exception:
            old_reference_date = str(self.config.reference_date)

        # 아카이브 경로 생성 (기존 DB의 기준년월 사용)
        build_date = datetime.now().strftime('%Y%m%d')
        stem = self.config.db_name.replace('.db', '')
        archive_path = self.config.archive_dir / f"{stem}_{old_reference_date}_{build_date}.db"

        # 아카이브 디렉토리 생성
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # 복사 (이동하지 않고 복사 - 새 DB 생성 실패 시 롤백 가능)
        shutil.copy2(self.db_path, archive_path)
        logger.info(f"기존 DB 아카이빙 완료: {archive_path}")

        return archive_path

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """인덱스 생성"""
        cursor = conn.cursor()

        # HR 테이블 인덱스
        for idx in HR_INDEXES:
            try:
                sql = f'CREATE INDEX IF NOT EXISTS {idx["name"]} ON HR("{idx["column"]}")'
                cursor.execute(sql)
                logger.debug(f"HR 인덱스 생성: {idx['name']}")
            except Exception as e:
                logger.warning(f"HR 인덱스 생성 실패 ({idx['name']}): {e}")

        # promotion_list 테이블 인덱스
        for idx in PROMOTION_INDEXES:
            try:
                sql = f'CREATE INDEX IF NOT EXISTS {idx["name"]} ON promotion_list("{idx["column"]}")'
                cursor.execute(sql)
                logger.debug(f"promotion_list 인덱스 생성: {idx['name']}")
            except Exception as e:
                logger.warning(f"promotion_list 인덱스 생성 실패 ({idx['name']}): {e}")

        conn.commit()
        logger.info("모든 인덱스 생성 완료")

    def _create_metadata_table(self, conn: sqlite3.Connection) -> None:
        """메타데이터 테이블 생성"""
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS _metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        metadata = {
            'schema_version': SCHEMA_VERSION,
            'created_at': datetime.now().isoformat(),
            'reference_date': str(self.config.reference_date),
            'source_csv_dir': str(self.config.csv_dir)
        }

        for key, value in metadata.items():
            cursor.execute(
                'INSERT OR REPLACE INTO _metadata (key, value) VALUES (?, ?)',
                (key, value)
            )

        conn.commit()
        logger.debug("메타데이터 테이블 생성 완료")


def verify_database(db_path: Path) -> Dict[str, Any]:
    """데이터베이스 검증

    Args:
        db_path: DB 파일 경로

    Returns:
        검증 결과 정보
    """
    result = {
        'valid': True,
        'tables': {},
        'errors': []
    }

    if not db_path.exists():
        result['valid'] = False
        result['errors'].append(f"데이터베이스 파일이 없습니다: {db_path}")
        return result

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 테이블 존재 확인
        for table in ['HR', 'promotion_list']:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                result['tables'][table] = {'exists': True, 'row_count': count}
            else:
                result['valid'] = False
                result['errors'].append(f"{table} 테이블이 없습니다")
                result['tables'][table] = {'exists': False, 'row_count': 0}

        # 메타데이터 확인
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_metadata'"
        )
        if cursor.fetchone():
            cursor.execute("SELECT key, value FROM _metadata")
            result['metadata'] = dict(cursor.fetchall())
        else:
            result['metadata'] = {}

        conn.close()

    except Exception as e:
        result['valid'] = False
        result['errors'].append(f"검증 실패: {e}")

    return result
