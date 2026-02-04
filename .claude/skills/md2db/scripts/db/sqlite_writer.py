# -*- coding: utf-8 -*-
"""
SQLite Database Writer for md2db v2

파싱된 데이터를 SQLite DB에 저장합니다.
v2에서는 중복/변경 감지 기능이 추가되었습니다.
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.models import Document, SourceFile
from core.utils import FileHasher
from db.schema import SCHEMA_V2, FTS_SCHEMA, SCHEMA_VERSION


def normalize_period(period_str: Optional[str]) -> Optional[str]:
    """기간 문자열을 YYYY-MM 형식으로 정규화

    지원 형식:
    - "2025년 11월" → "2025-11"
    - "2025년 9월" → "2025-09"
    - "2025-11" → "2025-11" (그대로)
    - "202511" → "2025-11"

    Args:
        period_str: 원본 기간 문자열

    Returns:
        정규화된 YYYY-MM 형식 또는 None
    """
    if not period_str:
        return None

    period_str = str(period_str).strip()

    # 이미 YYYY-MM 형식인 경우
    if re.match(r'^\d{4}-\d{2}$', period_str):
        return period_str

    # "2025년 11월" 또는 "2025년 9월" 형식
    match = re.match(r'^(\d{4})년\s*(\d{1,2})월', period_str)
    if match:
        year, month = match.groups()
        return f"{year}-{int(month):02d}"

    # "202511" 형식 (YYYYMM)
    match = re.match(r'^(\d{4})(\d{2})$', period_str)
    if match:
        year, month = match.groups()
        return f"{year}-{month}"

    # 인식 불가 시 원본 반환
    return period_str


class DatabaseWriter:
    """파싱된 데이터를 SQLite DB에 저장"""

    def __init__(self, db_path: str, append: bool = False):
        """
        Args:
            db_path: DB 파일 경로
            append: True면 기존 DB에 추가, False면 새로 생성
        """
        self.db_path = Path(db_path)
        self.append = append
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> None:
        """DB 연결 및 스키마 초기화"""
        if not self.append and self.db_path.exists():
            self.db_path.unlink()

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_schema(self) -> None:
        """스키마 초기화 (v2)"""
        cursor = self.conn.cursor()
        cursor.executescript(SCHEMA_V2)

        # 스키마 버전 기록
        cursor.execute("""
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES (?, ?)
        """, (SCHEMA_VERSION, 'md2db v2 - 증분 동기화, YAML 고도화, ChromaDB 통합'))

        # FTS 테이블 생성 시도 (실패해도 계속 진행)
        try:
            cursor.executescript(FTS_SCHEMA)
        except sqlite3.OperationalError:
            pass  # FTS5 미지원 환경

        self.conn.commit()

    def check_file_exists(self, file_hash: str) -> Optional[Dict]:
        """해시로 기존 파일 검색

        Args:
            file_hash: SHA256 해시

        Returns:
            source_files 레코드 (dict) 또는 None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sf.*, d.id as document_id
            FROM source_files sf
            LEFT JOIN documents d ON d.source_file_id = sf.id
            WHERE sf.file_hash = ? AND sf.status = 'processed'
        """, (file_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def check_file_by_path(self, file_path: str) -> Optional[Dict]:
        """경로로 기존 파일 검색

        Args:
            file_path: 파일 경로

        Returns:
            source_files 레코드 (dict) 또는 None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sf.*, d.id as document_id
            FROM source_files sf
            LEFT JOIN documents d ON d.source_file_id = sf.id
            WHERE sf.file_path = ? AND sf.status != 'deleted'
            ORDER BY sf.created_at DESC
            LIMIT 1
        """, (file_path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_document(self, doc: Document, filepath: str = None,
                      skip_if_exists: bool = True,
                      update_if_changed: bool = True) -> Tuple[int, str]:
        """문서 저장 (중복 감지 포함)

        Args:
            doc: Document 객체
            filepath: 원본 파일 경로 (중복 감지용)
            skip_if_exists: True면 동일 해시 파일 스킵
            update_if_changed: True면 변경된 파일 업데이트

        Returns:
            (doc_id, status) 튜플
            - status: 'created', 'skipped', 'updated'
        """
        source_file_id = None

        # 파일 지문 검사
        if filepath:
            fingerprint = FileHasher.fingerprint(filepath)

            # 동일 해시 파일 검색
            existing_by_hash = self.check_file_exists(fingerprint.file_hash)
            if existing_by_hash:
                if skip_if_exists:
                    return (existing_by_hash.get('document_id', 0), 'skipped')

            # 동일 경로 파일 검색 (변경 감지)
            existing_by_path = self.check_file_by_path(fingerprint.filepath)
            if existing_by_path:
                old_hash = existing_by_path.get('file_hash')
                if old_hash != fingerprint.file_hash:
                    # 파일이 변경됨
                    if update_if_changed:
                        # 기존 문서 삭제
                        if existing_by_path.get('document_id'):
                            self._delete_document(existing_by_path['document_id'])
                        # 기존 source_file 상태 업데이트
                        self._update_source_file_status(
                            existing_by_path['id'], 'deleted'
                        )
                else:
                    # 해시 동일 - 스킵
                    if skip_if_exists:
                        return (existing_by_path.get('document_id', 0), 'skipped')

            # source_file 레코드 생성
            source_file_id = self._save_source_file(fingerprint)

        # 문서 저장
        doc_id = self._save_document_impl(doc, source_file_id)

        # source_file 상태 업데이트
        if source_file_id:
            self._update_source_file_status(source_file_id, 'processed')
            self._link_document_to_source(source_file_id, doc_id)

        return (doc_id, 'created')

    def _save_source_file(self, fingerprint: SourceFile) -> int:
        """source_files 테이블에 저장"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO source_files (file_path, file_name, file_hash, file_size,
                                      encoding, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (
            fingerprint.filepath,
            fingerprint.filename,
            fingerprint.file_hash,
            fingerprint.file_size,
            fingerprint.encoding,
            datetime.now().isoformat(),
            fingerprint.updated_at.isoformat() if fingerprint.updated_at else None
        ))
        self.conn.commit()
        return cursor.lastrowid

    def _update_source_file_status(self, source_file_id: int, status: str,
                                   error_message: str = None) -> None:
        """source_file 상태 업데이트"""
        cursor = self.conn.cursor()
        if status == 'processed':
            cursor.execute("""
                UPDATE source_files
                SET status = ?, processed_at = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), source_file_id))
        elif status == 'error':
            cursor.execute("""
                UPDATE source_files
                SET status = ?, error_message = ?
                WHERE id = ?
            """, (status, error_message, source_file_id))
        else:
            cursor.execute("""
                UPDATE source_files SET status = ? WHERE id = ?
            """, (status, source_file_id))
        self.conn.commit()

    def _link_document_to_source(self, source_file_id: int, doc_id: int) -> None:
        """문서와 source_file 연결"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE documents SET source_file_id = ? WHERE id = ?
        """, (source_file_id, doc_id))
        self.conn.commit()

    def _delete_document(self, doc_id: int) -> None:
        """문서 삭제 (CASCADE로 관련 데이터도 삭제됨)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()

    def _save_document_impl(self, doc: Document, source_file_id: int = None) -> int:
        """문서 저장 구현부"""
        cursor = self.conn.cursor()

        # 전체 블록 수 및 단어 수 계산
        total_blocks = sum(len(s.blocks) for s in doc.sections)
        total_words = sum(
            sum(b.word_count for b in s.blocks)
            for s in doc.sections
        )

        # 문서 메타데이터 저장
        cursor.execute("""
            INSERT INTO documents (source_file_id, filename, title, file_size,
                                   total_sections, total_blocks, total_words, encoding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_file_id,
            doc.filename,
            doc.title,
            doc.file_size,
            len(doc.sections),
            total_blocks,
            total_words,
            doc.encoding
        ))
        doc_id = cursor.lastrowid

        # 프론트매터 저장 (v2: 별도 테이블)
        if doc.frontmatter:
            self._save_frontmatter(doc_id, doc.frontmatter)

        # 섹션 ID 매핑 (position -> db_id)
        section_id_map: Dict[int, int] = {}

        # 섹션 저장
        for i, section in enumerate(doc.sections):
            parent_db_id = section_id_map.get(section.parent_id) if section.parent_id is not None else None

            cursor.execute("""
                INSERT INTO sections (document_id, level, title, path, position,
                                      start_line, end_line, parent_id,
                                      word_count, has_subsections)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                section.level,
                section.title,
                section.path,
                section.position,
                section.start_line,
                section.end_line,
                parent_db_id,
                section.word_count,
                1 if section.has_subsections else 0
            ))
            section_id_map[i] = cursor.lastrowid

        # 블록 저장
        for i, section in enumerate(doc.sections):
            section_db_id = section_id_map[i]

            for j, block in enumerate(section.blocks):
                cursor.execute("""
                    INSERT INTO blocks (section_id, type, content, raw_markdown,
                                        position, start_line, end_line,
                                        word_count, char_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    section_db_id,
                    block.type.value,
                    block.content,
                    block.raw_markdown,
                    j,
                    block.start_line,
                    block.end_line,
                    block.word_count,
                    block.char_count,
                    json.dumps(block.metadata, ensure_ascii=False) if block.metadata else None
                ))

        self.conn.commit()
        return doc_id

    def _save_frontmatter(self, doc_id: int, frontmatter: Dict) -> None:
        """프론트매터 저장 (v2: 별도 테이블)"""
        cursor = self.conn.cursor()

        # 태그 처리
        tags = frontmatter.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        # 태그 저장 및 연결
        for tag_name in tags:
            if not tag_name:
                continue
            # 태그 삽입 (중복 무시)
            cursor.execute("""
                INSERT OR IGNORE INTO tags (tag_name) VALUES (?)
            """, (tag_name,))
            # 태그 ID 조회
            cursor.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
            tag_id = cursor.fetchone()[0]
            # 문서-태그 연결
            cursor.execute("""
                INSERT OR IGNORE INTO document_tags (document_id, tag_id)
                VALUES (?, ?)
            """, (doc_id, tag_id))

        # aliases 처리
        aliases = frontmatter.get('aliases', [])
        if isinstance(aliases, list):
            aliases_json = json.dumps(aliases, ensure_ascii=False)
        else:
            aliases_json = aliases

        # 커스텀 필드 (표준 필드 제외)
        standard_fields = {
            'title', 'author', 'type', 'status', 'source',
            'created', 'updated', 'date_consumed', 'period', 'aliases',
            'cssclass', 'tags'
        }
        custom_fields = {k: v for k, v in frontmatter.items() if k not in standard_fields}

        # period 정규화 (시계열 지원)
        period_raw = frontmatter.get('period')
        period_normalized = normalize_period(period_raw)

        cursor.execute("""
            INSERT INTO frontmatter (document_id, raw_yaml, parsed_json,
                                     title, author, type, status, source,
                                     created, updated, date_consumed, period,
                                     aliases, cssclass, tags_json, custom_fields)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            None,  # raw_yaml은 파서에서 설정
            json.dumps(frontmatter, ensure_ascii=False, default=str),
            frontmatter.get('title'),
            frontmatter.get('author'),
            frontmatter.get('type'),
            frontmatter.get('status'),
            frontmatter.get('source'),
            frontmatter.get('created'),
            frontmatter.get('updated'),
            frontmatter.get('date_consumed'),
            period_normalized,
            aliases_json,
            frontmatter.get('cssclass'),
            json.dumps(tags, ensure_ascii=False) if tags else None,
            json.dumps(custom_fields, ensure_ascii=False, default=str) if custom_fields else None
        ))

        self.conn.commit()

    def save_table_columns(self, block_id: int, columns: List[Dict]) -> None:
        """테이블 열 정보 저장

        Args:
            block_id: 블록 ID
            columns: [{'header_text': '열1', 'data_type': 'text', 'alignment': 'left'}, ...]
        """
        cursor = self.conn.cursor()
        for i, col in enumerate(columns):
            cursor.execute("""
                INSERT INTO table_columns (block_id, position, header_text,
                                           data_type, alignment)
                VALUES (?, ?, ?, ?, ?)
            """, (
                block_id,
                i,
                col.get('header_text'),
                col.get('data_type'),
                col.get('alignment', 'left')
            ))
        self.conn.commit()

    def update_chroma_sync(self, doc_id: int, collection_name: str,
                           chunk_count: int, embedding_model: str,
                           status: str = 'synced', error_message: str = None) -> None:
        """ChromaDB 동기화 상태 업데이트"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO chroma_sync
            (document_id, collection_name, chunk_count, embedding_model,
             synced_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            collection_name,
            chunk_count,
            embedding_model,
            datetime.now().isoformat() if status == 'synced' else None,
            status,
            error_message
        ))
        self.conn.commit()
