# -*- coding: utf-8 -*-
"""
SQLite Database Reader for md2db v2

DB에서 데이터를 읽어옵니다.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class DatabaseReader:
    """DB에서 데이터 읽기"""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: DB 파일 경로
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> None:
        """DB 연결"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"DB 파일을 찾을 수 없습니다: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_schema_version(self) -> int:
        """스키마 버전 조회"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] else 1
        except sqlite3.OperationalError:
            return 1  # schema_version 테이블 없음 = v1

    def get_info(self) -> Dict:
        """DB 정보 조회"""
        cursor = self.conn.cursor()

        # 스키마 버전
        schema_version = self.get_schema_version()

        # 문서 수
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        # 섹션 수
        cursor.execute("SELECT COUNT(*) FROM sections")
        section_count = cursor.fetchone()[0]

        # 블록 수
        cursor.execute("SELECT COUNT(*) FROM blocks")
        block_count = cursor.fetchone()[0]

        # 문서 목록
        cursor.execute("""
            SELECT id, filename, title, file_size, total_sections, total_blocks
            FROM documents
        """)
        documents = [dict(row) for row in cursor.fetchall()]

        # v2: source_files 정보
        source_files = []
        if schema_version >= 2:
            cursor.execute("""
                SELECT id, file_path, file_hash, file_size, status, processed_at
                FROM source_files
                WHERE status != 'deleted'
            """)
            source_files = [dict(row) for row in cursor.fetchall()]

        return {
            'schema_version': schema_version,
            'total_documents': doc_count,
            'total_sections': section_count,
            'total_blocks': block_count,
            'documents': documents,
            'source_files': source_files
        }

    def get_documents(self) -> List[Dict]:
        """문서 목록 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, filename, title, file_size, total_sections,
                   total_blocks, encoding, created_at
            FROM documents
            ORDER BY id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """특정 문서 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_frontmatter(self, doc_id: int) -> Optional[Dict]:
        """문서의 프론트매터 조회 (v2)"""
        if self.get_schema_version() < 2:
            # v1: documents.frontmatter 컬럼에서 읽기
            cursor = self.conn.cursor()
            cursor.execute("SELECT frontmatter FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row and row['frontmatter']:
                import json
                return json.loads(row['frontmatter'])
            return None

        # v2: frontmatter 테이블에서 읽기
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM frontmatter WHERE document_id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_sections(self, document_id: int = None) -> List[Dict]:
        """섹션 목록 조회"""
        cursor = self.conn.cursor()

        if document_id:
            cursor.execute("""
                SELECT s.*, d.filename
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                WHERE s.document_id = ?
                ORDER BY s.position
            """, (document_id,))
        else:
            cursor.execute("""
                SELECT s.*, d.filename
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                ORDER BY s.document_id, s.position
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_section_by_path(self, path: str, document_id: int = None) -> Optional[Dict]:
        """경로로 섹션 조회"""
        cursor = self.conn.cursor()

        if document_id:
            cursor.execute("""
                SELECT * FROM sections
                WHERE path = ? AND document_id = ?
            """, (path, document_id))
        else:
            cursor.execute("SELECT * FROM sections WHERE path = ?", (path,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_blocks(self, section_id: int) -> List[Dict]:
        """섹션의 블록 목록 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM blocks
            WHERE section_id = ?
            ORDER BY position
        """, (section_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_all_blocks(self, document_id: int = None) -> List[Dict]:
        """모든 블록 조회 (문서별 필터링 가능)"""
        cursor = self.conn.cursor()

        if document_id:
            cursor.execute("""
                SELECT b.*, s.path as section_path, s.title as section_title
                FROM blocks b
                JOIN sections s ON b.section_id = s.id
                WHERE s.document_id = ?
                ORDER BY s.position, b.position
            """, (document_id,))
        else:
            cursor.execute("""
                SELECT b.*, s.path as section_path, s.title as section_title,
                       d.filename
                FROM blocks b
                JOIN sections s ON b.section_id = s.id
                JOIN documents d ON s.document_id = d.id
                ORDER BY d.id, s.position, b.position
            """)

        return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, document_id: int = None) -> List[Dict]:
        """전문 검색"""
        cursor = self.conn.cursor()

        # FTS 테이블 존재 확인
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='blocks_fts'
        """)

        if cursor.fetchone():
            # FTS5 검색
            if document_id:
                cursor.execute("""
                    SELECT b.*, s.title as section_title, s.path as section_path
                    FROM blocks b
                    JOIN blocks_fts fts ON b.id = fts.rowid
                    JOIN sections s ON b.section_id = s.id
                    WHERE blocks_fts MATCH ? AND s.document_id = ?
                """, (query, document_id))
            else:
                cursor.execute("""
                    SELECT b.*, s.title as section_title, s.path as section_path,
                           d.filename
                    FROM blocks b
                    JOIN blocks_fts fts ON b.id = fts.rowid
                    JOIN sections s ON b.section_id = s.id
                    JOIN documents d ON s.document_id = d.id
                    WHERE blocks_fts MATCH ?
                """, (query,))
        else:
            # 일반 LIKE 검색
            like_query = f'%{query}%'
            if document_id:
                cursor.execute("""
                    SELECT b.*, s.title as section_title, s.path as section_path
                    FROM blocks b
                    JOIN sections s ON b.section_id = s.id
                    WHERE (b.content LIKE ? OR b.raw_markdown LIKE ?)
                      AND s.document_id = ?
                """, (like_query, like_query, document_id))
            else:
                cursor.execute("""
                    SELECT b.*, s.title as section_title, s.path as section_path,
                           d.filename
                    FROM blocks b
                    JOIN sections s ON b.section_id = s.id
                    JOIN documents d ON s.document_id = d.id
                    WHERE b.content LIKE ? OR b.raw_markdown LIKE ?
                """, (like_query, like_query))

        return [dict(row) for row in cursor.fetchall()]

    def get_section_tree(self, section_id: int) -> List[int]:
        """섹션과 모든 하위 섹션 ID 목록"""
        cursor = self.conn.cursor()

        # 해당 섹션 정보
        cursor.execute("SELECT path, document_id FROM sections WHERE id = ?", (section_id,))
        row = cursor.fetchone()
        if not row:
            return []

        path_prefix = row['path']
        doc_id = row['document_id']

        # 해당 경로로 시작하는 모든 섹션
        cursor.execute("""
            SELECT id FROM sections
            WHERE document_id = ? AND (path = ? OR path LIKE ?)
            ORDER BY position
        """, (doc_id, path_prefix, f'{path_prefix}.%'))

        return [r['id'] for r in cursor.fetchall()]

    def get_tags(self, document_id: int = None) -> List[Dict]:
        """태그 목록 조회 (v2)"""
        if self.get_schema_version() < 2:
            return []

        cursor = self.conn.cursor()

        if document_id:
            cursor.execute("""
                SELECT t.id, t.tag_name, COUNT(dt.document_id) as doc_count
                FROM tags t
                JOIN document_tags dt ON t.id = dt.tag_id
                WHERE dt.document_id = ?
                GROUP BY t.id
            """, (document_id,))
        else:
            cursor.execute("""
                SELECT t.id, t.tag_name, COUNT(dt.document_id) as doc_count
                FROM tags t
                LEFT JOIN document_tags dt ON t.id = dt.tag_id
                GROUP BY t.id
                ORDER BY doc_count DESC
            """)

        return [dict(row) for row in cursor.fetchall()]

    def get_documents_by_tag(self, tag_name: str) -> List[Dict]:
        """태그로 문서 검색 (v2)"""
        if self.get_schema_version() < 2:
            return []

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT d.*
            FROM documents d
            JOIN document_tags dt ON d.id = dt.document_id
            JOIN tags t ON dt.tag_id = t.id
            WHERE t.tag_name = ?
        """, (tag_name,))

        return [dict(row) for row in cursor.fetchall()]

    def get_chroma_sync_status(self, document_id: int = None) -> List[Dict]:
        """ChromaDB 동기화 상태 조회 (v2)"""
        if self.get_schema_version() < 2:
            return []

        cursor = self.conn.cursor()

        if document_id:
            cursor.execute("""
                SELECT * FROM chroma_sync WHERE document_id = ?
            """, (document_id,))
        else:
            cursor.execute("SELECT * FROM chroma_sync")

        return [dict(row) for row in cursor.fetchall()]

    def get_table_columns(self, block_id: int) -> List[Dict]:
        """테이블 열 정보 조회 (v2)"""
        if self.get_schema_version() < 2:
            return []

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM table_columns
            WHERE block_id = ?
            ORDER BY position
        """, (block_id,))

        return [dict(row) for row in cursor.fetchall()]
