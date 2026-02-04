# -*- coding: utf-8 -*-
"""
Database Migrator for md2db

v1 → v2 스키마 마이그레이션을 수행합니다.
"""

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from db.schema import SCHEMA_VERSION, SCHEMA_V2, FTS_SCHEMA


class Migrator:
    """DB 스키마 마이그레이션"""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: DB 파일 경로
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def get_current_version(self) -> int:
        """현재 스키마 버전 조회"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            version = row[0] if row and row[0] else 1
        except sqlite3.OperationalError:
            version = 1  # schema_version 테이블 없음 = v1
        finally:
            conn.close()

        return version

    def needs_migration(self) -> bool:
        """마이그레이션 필요 여부"""
        return self.get_current_version() < SCHEMA_VERSION

    def backup(self) -> Path:
        """DB 백업 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.db_path.with_suffix(f'.v1_backup_{timestamp}.db')
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def migrate(self, create_backup: bool = True) -> dict:
        """마이그레이션 실행

        Args:
            create_backup: 백업 생성 여부

        Returns:
            마이그레이션 결과 정보
        """
        current_version = self.get_current_version()

        if current_version >= SCHEMA_VERSION:
            return {
                'status': 'skipped',
                'message': f'이미 v{SCHEMA_VERSION} 스키마입니다.',
                'from_version': current_version,
                'to_version': SCHEMA_VERSION
            }

        # 백업 생성
        backup_path = None
        if create_backup:
            backup_path = self.backup()

        # 마이그레이션 실행
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        try:
            if current_version == 1:
                self._migrate_v1_to_v2()

            return {
                'status': 'success',
                'message': f'v{current_version} → v{SCHEMA_VERSION} 마이그레이션 완료',
                'from_version': current_version,
                'to_version': SCHEMA_VERSION,
                'backup_path': str(backup_path) if backup_path else None
            }

        except Exception as e:
            self.conn.rollback()
            return {
                'status': 'error',
                'message': str(e),
                'from_version': current_version,
                'to_version': SCHEMA_VERSION,
                'backup_path': str(backup_path) if backup_path else None
            }

        finally:
            self.conn.close()
            self.conn = None

    def _migrate_v1_to_v2(self) -> None:
        """v1 → v2 마이그레이션"""
        cursor = self.conn.cursor()

        # 1. schema_version 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now', 'localtime')),
                description TEXT
            )
        """)

        # 2. source_files 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER,
                encoding TEXT DEFAULT 'utf-8',
                status TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processed', 'error', 'deleted')),
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT,
                processed_at TEXT,
                UNIQUE (file_path, file_hash)
            )
        """)

        # 3. documents 테이블에 source_file_id 컬럼 추가
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN source_file_id INTEGER")
        except sqlite3.OperationalError:
            pass  # 이미 존재

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN total_words INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 4. frontmatter 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frontmatter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                raw_yaml TEXT,
                parsed_json TEXT,
                title TEXT,
                author TEXT,
                type TEXT,
                status TEXT,
                source TEXT,
                created TEXT,
                updated TEXT,
                date_consumed TEXT,
                aliases TEXT,
                cssclass TEXT,
                tags_json TEXT,
                custom_fields TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # 5. 기존 documents.frontmatter 데이터 이전
        cursor.execute("SELECT id, frontmatter FROM documents WHERE frontmatter IS NOT NULL")
        for row in cursor.fetchall():
            doc_id = row['id']
            fm_json = row['frontmatter']
            if fm_json:
                try:
                    fm_data = json.loads(fm_json)
                    cursor.execute("""
                        INSERT OR IGNORE INTO frontmatter (document_id, parsed_json, title, author, type)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        fm_json,
                        fm_data.get('title'),
                        fm_data.get('author'),
                        fm_data.get('type')
                    ))
                except json.JSONDecodeError:
                    pass

        # 6. tags, document_tags 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (document_id, tag_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # 7. sections 테이블에 새 컬럼 추가
        try:
            cursor.execute("ALTER TABLE sections ADD COLUMN word_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE sections ADD COLUMN has_subsections INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 8. blocks 테이블에 새 컬럼 추가
        try:
            cursor.execute("ALTER TABLE blocks ADD COLUMN word_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE blocks ADD COLUMN char_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 9. block_metadata 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS block_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE,
                UNIQUE (block_id, key)
            )
        """)

        # 10. table_columns 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                header_text TEXT,
                data_type TEXT,
                alignment TEXT DEFAULT 'left'
                    CHECK (alignment IN ('left', 'center', 'right')),
                FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
            )
        """)

        # 11. chroma_sync 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chroma_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                collection_name TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                embedding_model TEXT,
                synced_at TEXT,
                status TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending', 'synced', 'error', 'outdated')),
                error_message TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE (document_id, collection_name)
            )
        """)

        # 12. 새 인덱스 생성
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_source_files_hash ON source_files(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_source_files_path ON source_files(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_source_files_status ON source_files(status)",
            "CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_file_id)",
            "CREATE INDEX IF NOT EXISTS idx_frontmatter_doc ON frontmatter(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_frontmatter_author ON frontmatter(author)",
            "CREATE INDEX IF NOT EXISTS idx_frontmatter_type ON frontmatter(type)",
            "CREATE INDEX IF NOT EXISTS idx_chroma_doc ON chroma_sync(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_chroma_status ON chroma_sync(status)",
        ]

        for stmt in index_statements:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass

        # 13. 스키마 버전 업데이트
        cursor.execute("""
            INSERT OR REPLACE INTO schema_version (version, description)
            VALUES (?, ?)
        """, (SCHEMA_VERSION, 'v1 → v2 마이그레이션: source_files, frontmatter, tags 등 추가'))

        self.conn.commit()
