#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
study2db - 학습 자료 통합 DB 변환기 v1.1.0

다양한 형식의 파일(md, txt, csv, db, pdf)을 SQLite DB로 변환하여
AI가 효율적으로 조회/활용할 수 있도록 합니다.

Usage:
    # 파일 임포트
    python study2db.py import output.db file1.md file2.pdf --name "프로젝트명"

    # 정보 조회
    python study2db.py info study.db
    python study2db.py files study.db
    python study2db.py summary study.db

    # 검색
    python study2db.py search study.db "키워드"
    python study2db.py search study.db "키워드" --type fact --importance 4

    # LLM 핵심 추출
    python study2db.py extract study.db
    python study2db.py extract study.db --file-id 1

    # 마이그레이션 (v1 → v2)
    python study2db.py migrate study.db
"""

import re
import sys
import os
import sqlite3
import json
import argparse
import hashlib
import csv
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Windows 환경에서 UTF-8 출력 보장
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ============================================
# 상수 정의
# ============================================

SCHEMA_VERSION = 2  # 현재 스키마 버전

# PyYAML 사용 가능 여부
HAS_YAML = False
try:
    import yaml
    HAS_YAML = True
except ImportError:
    pass

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.csv', '.db', '.pdf'}

class ChunkType(Enum):
    """청크 유형"""
    SECTION = "section"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    CODE = "code"
    LIST = "list"
    FRONTMATTER = "frontmatter"
    DATA_ROW = "data_row"


class InsightType(Enum):
    """인사이트 유형"""
    SUMMARY = "summary"
    KEY_POINT = "key_point"
    DEFINITION = "definition"
    FACT = "fact"
    RECOMMENDATION = "recommendation"


# ============================================
# 데이터 클래스
# ============================================

@dataclass
class Chunk:
    """콘텐츠 청크"""
    chunk_type: str
    content: str
    title: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    metadata: Dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass
class Insight:
    """핵심 인사이트"""
    insight_type: str
    content: str
    importance: int = 3
    keywords: List[str] = field(default_factory=list)


# ============================================
# 유틸리티 함수
# ============================================

def detect_encoding(file_path: Path) -> str:
    """파일 인코딩 자동 감지"""
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(1024)  # 샘플 읽기
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'utf-8'  # 기본값


def calculate_file_hash(file_path: Path) -> str:
    """파일 SHA256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def format_path(path: str) -> str:
    """경로를 >> 형식으로 변환"""
    return path.replace('\\', ' >> ').replace('/', ' >> ')


# ============================================
# YAML 파서 클래스
# ============================================

class YamlParser:
    """YAML 프론트매터 파서 (PyYAML 기반, fallback 지원)"""

    def parse(self, content: str) -> Dict[str, Any]:
        """YAML 문자열을 딕셔너리로 파싱"""
        if not content or not content.strip():
            return {}

        if HAS_YAML:
            try:
                result = yaml.safe_load(content)
                return result if isinstance(result, dict) else {}
            except yaml.YAMLError:
                return self._fallback_parse(content)
        else:
            return self._fallback_parse(content)

    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        """단순 key: value 파싱 (PyYAML 없을 때)"""
        result = {}
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                # 간단한 배열 처리 [item1, item2]
                if value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    result[key] = [item.strip().strip('"\'') for item in items if item.strip()]
                # 인용 부호 제거
                elif value.startswith('"') and value.endswith('"'):
                    result[key] = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    result[key] = value[1:-1]
                elif value:
                    result[key] = value

        return result


# ============================================
# 파서 클래스
# ============================================

class MarkdownParser:
    """마크다운 파일 파서"""

    def __init__(self):
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s+(.+)$'),
            'frontmatter_start': re.compile(r'^---\s*$'),
            'code_fence': re.compile(r'^(`{3,}|~{3,})(\w*)?'),
            'list_item': re.compile(r'^(\s*)([-*+]|\d+\.)\s+'),
            'table_row': re.compile(r'^\s*\|.+\|\s*$'),
        }
        self.yaml_parser = YamlParser()

    def parse(self, file_path: Path) -> List[Chunk]:
        """마크다운 파일을 청크로 분리"""
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        lines = content.split('\n')
        chunks = []

        i = 0
        # 프론트매터 처리 (YamlParser 사용)
        if lines and self.patterns['frontmatter_start'].match(lines[0]):
            fm_end = -1
            for j in range(1, len(lines)):
                if self.patterns['frontmatter_start'].match(lines[j]):
                    fm_end = j
                    break
            if fm_end > 0:
                fm_content = '\n'.join(lines[1:fm_end])
                # YAML 파싱 (PyYAML 또는 fallback)
                parsed_yaml = self.yaml_parser.parse(fm_content)
                chunks.append(Chunk(
                    chunk_type=ChunkType.FRONTMATTER.value,
                    content=fm_content,
                    title="frontmatter",
                    start_line=1,
                    end_line=fm_end + 1,
                    metadata={'parsed': parsed_yaml}  # 파싱된 YAML 저장
                ))
                i = fm_end + 1

        # 헤더 기반 섹션 분리
        current_section_start = i
        current_section_title = None
        current_section_level = 0
        buffer = []

        while i < len(lines):
            line = lines[i]
            header_match = self.patterns['header'].match(line)

            if header_match:
                # 이전 섹션 저장
                if buffer:
                    section_content = '\n'.join(buffer).strip()
                    if section_content:
                        chunks.append(Chunk(
                            chunk_type=ChunkType.SECTION.value,
                            content=section_content,
                            title=current_section_title,
                            start_line=current_section_start + 1,
                            end_line=i,
                            metadata={'level': current_section_level}
                        ))

                # 새 섹션 시작
                current_section_level = len(header_match.group(1))
                current_section_title = header_match.group(2).strip()
                current_section_start = i
                buffer = [line]
            else:
                buffer.append(line)

            i += 1

        # 마지막 섹션 저장
        if buffer:
            section_content = '\n'.join(buffer).strip()
            if section_content:
                chunks.append(Chunk(
                    chunk_type=ChunkType.SECTION.value,
                    content=section_content,
                    title=current_section_title,
                    start_line=current_section_start + 1,
                    end_line=len(lines),
                    metadata={'level': current_section_level}
                ))

        return chunks


class TextParser:
    """텍스트 파일 파서"""

    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size

    def parse(self, file_path: Path) -> List[Chunk]:
        """텍스트 파일을 청크로 분리"""
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        # 빈 줄 기준 단락 분리
        paragraphs = re.split(r'\n\s*\n', content)
        chunks = []
        current_line = 1

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            para_lines = para.count('\n') + 1

            # 청크 크기 제한
            if len(para) > self.max_chunk_size:
                # 큰 단락은 문장 단위로 분리
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_buffer = []
                sub_start = current_line

                for sent in sentences:
                    if sum(len(s) for s in sub_buffer) + len(sent) > self.max_chunk_size and sub_buffer:
                        chunks.append(Chunk(
                            chunk_type=ChunkType.PARAGRAPH.value,
                            content=' '.join(sub_buffer),
                            start_line=sub_start,
                            end_line=current_line
                        ))
                        sub_buffer = []
                        sub_start = current_line
                    sub_buffer.append(sent)

                if sub_buffer:
                    chunks.append(Chunk(
                        chunk_type=ChunkType.PARAGRAPH.value,
                        content=' '.join(sub_buffer),
                        start_line=sub_start,
                        end_line=current_line + para_lines
                    ))
            else:
                chunks.append(Chunk(
                    chunk_type=ChunkType.PARAGRAPH.value,
                    content=para,
                    start_line=current_line,
                    end_line=current_line + para_lines
                ))

            current_line += para_lines + 1  # +1 for blank line

        return chunks


class CsvParser:
    """CSV 파일 파서"""

    def parse(self, file_path: Path) -> Tuple[List[Chunk], List[Dict]]:
        """CSV 파일을 청크와 구조화 데이터로 분리"""
        encoding = detect_encoding(file_path)

        # pandas 사용 시도
        try:
            import pandas as pd
            df = pd.read_csv(file_path, encoding=encoding)

            # 전체 요약 청크
            summary = f"CSV 파일: {file_path.name}\n"
            summary += f"행 수: {len(df)}, 열 수: {len(df.columns)}\n"
            summary += f"컬럼: {', '.join(df.columns.tolist())}\n"

            # 수치 컬럼 통계
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary += "\n[수치 컬럼 통계]\n"
                for col in numeric_cols[:5]:  # 최대 5개
                    summary += f"- {col}: 평균={df[col].mean():.2f}, 최소={df[col].min()}, 최대={df[col].max()}\n"

            chunks = [Chunk(
                chunk_type=ChunkType.TABLE.value,
                content=summary,
                title=file_path.stem,
                metadata={'columns': df.columns.tolist(), 'row_count': len(df)}
            )]

            # 구조화 데이터
            structured = []
            for idx, row in df.iterrows():
                structured.append({
                    'row_index': idx,
                    'data': row.to_dict()
                })

            return chunks, structured

        except ImportError:
            # pandas 없으면 표준 csv 모듈 사용
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                return [], []

            columns = list(rows[0].keys())
            summary = f"CSV 파일: {file_path.name}\n"
            summary += f"행 수: {len(rows)}, 열 수: {len(columns)}\n"
            summary += f"컬럼: {', '.join(columns)}\n"

            chunks = [Chunk(
                chunk_type=ChunkType.TABLE.value,
                content=summary,
                title=file_path.stem,
                metadata={'columns': columns, 'row_count': len(rows)}
            )]

            structured = [{'row_index': i, 'data': row} for i, row in enumerate(rows)]

            return chunks, structured


class DbParser:
    """SQLite DB 파일 파서 - md2db 스키마 자동 감지"""

    def parse(self, file_path: Path) -> Tuple[List[Chunk], List[Dict]]:
        """DB 파일 파싱 (md2db DB는 블록 내용 추출)"""
        chunks = []
        tables_info = []

        try:
            conn = sqlite3.connect(str(file_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 테이블 목록 조회
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            # md2db 스키마 감지
            if self._is_md2db_schema(tables):
                chunks, tables_info = self._parse_md2db(cursor, file_path)
            else:
                chunks, tables_info = self._parse_generic_db(cursor, file_path, tables)

            conn.close()

        except Exception as e:
            chunks.append(Chunk(
                chunk_type=ChunkType.PARAGRAPH.value,
                content=f"DB 파싱 오류: {str(e)}",
                title=file_path.stem
            ))

        return chunks, tables_info

    def _is_md2db_schema(self, tables: List[str]) -> bool:
        """md2db로 생성된 DB인지 확인"""
        required = {'documents', 'sections', 'blocks'}
        return required.issubset(set(tables))

    def _parse_md2db(self, cursor, file_path: Path) -> Tuple[List[Chunk], List[Dict]]:
        """md2db DB에서 블록 내용 추출"""
        chunks = []

        # 문서 정보 먼저 추가
        cursor.execute("SELECT id, filename, title, total_sections, total_blocks FROM documents")
        docs = cursor.fetchall()

        doc_summary = f"md2db DB: {file_path.name}\n"
        doc_summary += f"문서 수: {len(docs)}\n\n"
        for doc in docs:
            doc_summary += f"- {doc['filename']}: {doc['title']} ({doc['total_blocks']} blocks)\n"

        chunks.append(Chunk(
            chunk_type=ChunkType.TABLE.value,
            content=doc_summary,
            title=f"{file_path.stem} (개요)",
            metadata={'type': 'md2db_summary', 'doc_count': len(docs)}
        ))

        # 섹션별 블록 내용 추출
        cursor.execute("""
            SELECT d.filename, d.title as doc_title, s.title as section_title,
                   s.level, b.content, b.type as block_type
            FROM blocks b
            JOIN sections s ON b.section_id = s.id
            JOIN documents d ON s.document_id = d.id
            WHERE b.type != 'header' AND LENGTH(b.content) > 50
            ORDER BY d.id, s.position, b.position
        """)

        for row in cursor.fetchall():
            content = row['content'].strip() if row['content'] else ''
            if content:
                section_title = row['section_title'] or '(본문)'
                chunks.append(Chunk(
                    chunk_type=ChunkType.SECTION.value,
                    content=content,
                    title=f"{row['filename']} > {section_title}",
                    metadata={
                        'doc_title': row['doc_title'],
                        'block_type': row['block_type'],
                        'level': row['level']
                    }
                ))

        return chunks, []

    def _parse_generic_db(self, cursor, file_path: Path, tables: List[str]) -> Tuple[List[Chunk], List[Dict]]:
        """일반 DB의 메타데이터 추출"""
        chunks = []
        tables_info = []

        summary = f"SQLite DB: {file_path.name}\n"
        summary += f"테이블 수: {len(tables)}\n\n"

        for table in tables:
            # 스키마 정보
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            col_info = [{'name': c['name'], 'type': c['type']} for c in columns]

            # 행 수
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            summary += f"[{table}] {row_count}행\n"
            summary += f"  컬럼: {', '.join(c['name'] for c in col_info)}\n\n"

            tables_info.append({
                'original_table': table,
                'imported_table': f'ext_{table}',
                'row_count': row_count,
                'schema': col_info
            })

        chunks.append(Chunk(
            chunk_type=ChunkType.TABLE.value,
            content=summary,
            title=file_path.stem,
            metadata={'tables': tables}
        ))

        return chunks, tables_info


class PdfParser:
    """PDF 파일 파서"""

    def parse(self, file_path: Path) -> List[Chunk]:
        """PDF 파일을 청크로 분리"""
        chunks = []

        # pdfplumber 시도
        try:
            import pdfplumber

            with pdfplumber.open(str(file_path)) as pdf:
                full_text = []
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        full_text.append(f"[Page {i+1}]\n{text}")

                combined = '\n\n'.join(full_text)

                # 페이지별 또는 섹션별 분리
                if len(combined) > 2000:
                    # 큰 PDF는 페이지별로 청크
                    for i, page_text in enumerate(full_text):
                        chunks.append(Chunk(
                            chunk_type=ChunkType.SECTION.value,
                            content=page_text,
                            title=f"Page {i+1}",
                            metadata={'page': i+1}
                        ))
                else:
                    chunks.append(Chunk(
                        chunk_type=ChunkType.PARAGRAPH.value,
                        content=combined,
                        title=file_path.stem
                    ))

        except ImportError:
            chunks.append(Chunk(
                chunk_type=ChunkType.PARAGRAPH.value,
                content=f"PDF 파싱 실패: pdfplumber가 설치되지 않음. pip install pdfplumber",
                title=file_path.stem
            ))
        except Exception as e:
            chunks.append(Chunk(
                chunk_type=ChunkType.PARAGRAPH.value,
                content=f"PDF 파싱 오류: {str(e)}",
                title=file_path.stem
            ))

        return chunks


# ============================================
# DB 관리자 클래스
# ============================================

class DatabaseManager:
    """SQLite DB 관리"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """DB 연결"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA encoding = 'UTF-8'")

    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_schema_version(self) -> int:
        """현재 DB 스키마 버전 조회"""
        try:
            cursor = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                return 1  # schema_version 테이블 없으면 v1

            cursor = self.conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] else 1
        except sqlite3.Error:
            return 1

    def backup(self) -> str:
        """DB 백업 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = str(self.db_path).replace('.db', f'.v1_backup_{timestamp}.db')

        import shutil
        shutil.copy2(str(self.db_path), backup_path)
        return backup_path

    def migrate(self, create_backup: bool = True) -> Dict[str, Any]:
        """스키마 마이그레이션 실행"""
        current_version = self.get_schema_version()

        if current_version >= SCHEMA_VERSION:
            return {
                'status': 'skipped',
                'message': f'이미 최신 버전입니다 (v{current_version})',
                'current_version': current_version
            }

        # 백업 생성
        backup_path = None
        if create_backup:
            backup_path = self.backup()
            print(f"백업 생성: {backup_path}")

        try:
            if current_version == 1:
                self._migrate_v1_to_v2()

            return {
                'status': 'success',
                'message': f'v{current_version} → v{SCHEMA_VERSION} 마이그레이션 완료',
                'backup_path': backup_path,
                'previous_version': current_version,
                'current_version': SCHEMA_VERSION
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'마이그레이션 실패: {str(e)}',
                'backup_path': backup_path
            }

    def _migrate_v1_to_v2(self):
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

        # 2. 버전 기록
        cursor.execute("""
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES (?, ?)
        """, (SCHEMA_VERSION, 'v1.1.0 - 스키마 버전 관리 도입, YAML 파싱 고도화'))

        self.conn.commit()
        print(f"스키마 버전 {SCHEMA_VERSION} 적용 완료")

    def init_schema(self):
        """스키마 초기화"""
        # 인라인 스키마 직접 사용 (안정적)
        self._create_inline_schema()

    def _create_inline_schema(self):
        """인라인 스키마 생성 (백업)"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now', 'localtime')),
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS study_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                purpose TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS source_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                encoding TEXT DEFAULT 'utf-8',
                processed_at TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                FOREIGN KEY (project_id) REFERENCES study_projects(id)
            );

            CREATE TABLE IF NOT EXISTS content_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_type TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                word_count INTEGER,
                start_line INTEGER,
                end_line INTEGER,
                metadata TEXT,
                FOREIGN KEY (file_id) REFERENCES source_files(id)
            );

            CREATE TABLE IF NOT EXISTS key_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id INTEGER,
                file_id INTEGER NOT NULL,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 3,
                keywords TEXT,
                extracted_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (chunk_id) REFERENCES content_chunks(id),
                FOREIGN KEY (file_id) REFERENCES source_files(id)
            );

            CREATE TABLE IF NOT EXISTS structured_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                table_name TEXT,
                row_index INTEGER NOT NULL,
                data_json TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES source_files(id)
            );

            CREATE TABLE IF NOT EXISTS external_db_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                original_table TEXT NOT NULL,
                imported_table TEXT NOT NULL,
                row_count INTEGER,
                schema_json TEXT,
                FOREIGN KEY (file_id) REFERENCES source_files(id)
            );
        """)
        self.conn.commit()

        # FTS 테이블 생성 (별도 실행)
        try:
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                    title, content, content=content_chunks, content_rowid=id
                )
            """)
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts USING fts5(
                    content, keywords, content=key_insights, content_rowid=id
                )
            """)
            self.conn.commit()
        except sqlite3.Error:
            pass  # FTS 이미 존재하면 무시

        # 스키마 버전 삽입 (새 DB 생성 시)
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO schema_version (version, description)
                VALUES (?, ?)
            """, (SCHEMA_VERSION, 'v1.1.0 - 스키마 버전 관리 도입, YAML 파싱 고도화'))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def create_project(self, name: str, purpose: str = None) -> int:
        """프로젝트 생성"""
        cursor = self.conn.execute(
            "INSERT INTO study_projects (name, purpose) VALUES (?, ?)",
            (name, purpose)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_project(self) -> Optional[Dict]:
        """첫 번째 프로젝트 조회"""
        cursor = self.conn.execute("SELECT * FROM study_projects LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_file(self, project_id: int, file_path: Path) -> int:
        """파일 추가"""
        file_hash = calculate_file_hash(file_path)
        encoding = detect_encoding(file_path)

        cursor = self.conn.execute("""
            INSERT OR IGNORE INTO source_files
            (project_id, file_path, file_name, file_type, file_size, file_hash, encoding, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            project_id,
            str(file_path.absolute()),
            file_path.name,
            file_path.suffix.lower().lstrip('.'),
            file_path.stat().st_size,
            file_hash,
            encoding
        ))
        self.conn.commit()

        if cursor.rowcount == 0:
            # 이미 존재하는 파일
            cursor = self.conn.execute(
                "SELECT id FROM source_files WHERE project_id = ? AND file_hash = ?",
                (project_id, file_hash)
            )
            return cursor.fetchone()[0]
        return cursor.lastrowid

    def save_chunks(self, file_id: int, chunks: List[Chunk]):
        """청크 저장"""
        for i, chunk in enumerate(chunks):
            self.conn.execute("""
                INSERT INTO content_chunks
                (file_id, chunk_index, chunk_type, title, content, word_count, start_line, end_line, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, i,
                chunk.chunk_type,
                chunk.title,
                chunk.content,
                chunk.word_count,
                chunk.start_line,
                chunk.end_line,
                json.dumps(chunk.metadata, ensure_ascii=False) if chunk.metadata else None
            ))
        self.conn.commit()

    def save_structured_data(self, file_id: int, table_name: str, rows: List[Dict]):
        """구조화 데이터 저장"""
        for row in rows:
            self.conn.execute("""
                INSERT INTO structured_data (file_id, table_name, row_index, data_json)
                VALUES (?, ?, ?, ?)
            """, (
                file_id,
                table_name,
                row['row_index'],
                json.dumps(row['data'], ensure_ascii=False, default=str)
            ))
        self.conn.commit()

    def save_db_table_info(self, file_id: int, tables_info: List[Dict]):
        """외부 DB 테이블 정보 저장"""
        for info in tables_info:
            self.conn.execute("""
                INSERT INTO external_db_tables
                (file_id, original_table, imported_table, row_count, schema_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                file_id,
                info['original_table'],
                info['imported_table'],
                info['row_count'],
                json.dumps(info['schema'], ensure_ascii=False)
            ))
        self.conn.commit()

    def update_file_status(self, file_id: int, status: str, error_msg: str = None):
        """파일 상태 업데이트"""
        self.conn.execute("""
            UPDATE source_files
            SET status = ?, error_message = ?, processed_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (status, error_msg, file_id))
        self.conn.commit()

    def save_insights(self, file_id: int, chunk_id: Optional[int], insights: List[Insight]):
        """인사이트 저장"""
        for insight in insights:
            self.conn.execute("""
                INSERT INTO key_insights
                (chunk_id, file_id, insight_type, content, importance, keywords)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                file_id,
                insight.insight_type,
                insight.content,
                insight.importance,
                json.dumps(insight.keywords, ensure_ascii=False) if insight.keywords else None
            ))
        self.conn.commit()

    def get_chunks_for_extraction(self, file_id: Optional[int] = None) -> List[Dict]:
        """추출 대상 청크 조회"""
        if file_id:
            cursor = self.conn.execute("""
                SELECT cc.id, cc.file_id, cc.content, cc.title, sf.file_name
                FROM content_chunks cc
                JOIN source_files sf ON cc.file_id = sf.id
                WHERE cc.file_id = ? AND cc.id NOT IN (SELECT DISTINCT chunk_id FROM key_insights WHERE chunk_id IS NOT NULL)
            """, (file_id,))
        else:
            cursor = self.conn.execute("""
                SELECT cc.id, cc.file_id, cc.content, cc.title, sf.file_name
                FROM content_chunks cc
                JOIN source_files sf ON cc.file_id = sf.id
                WHERE cc.id NOT IN (SELECT DISTINCT chunk_id FROM key_insights WHERE chunk_id IS NOT NULL)
            """)
        return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, insight_type: str = None, importance: int = None) -> List[Dict]:
        """검색 (LIKE 기반)"""
        sql = """
            SELECT ki.content, ki.insight_type, ki.importance, ki.keywords,
                   sf.file_name, cc.title as source_section
            FROM key_insights ki
            JOIN source_files sf ON ki.file_id = sf.id
            LEFT JOIN content_chunks cc ON ki.chunk_id = cc.id
            WHERE ki.content LIKE ?
        """
        params = [f'%{query}%']

        if insight_type:
            sql += " AND ki.insight_type = ?"
            params.append(insight_type)
        if importance:
            sql += " AND ki.importance >= ?"
            params.append(importance)

        sql += " ORDER BY ki.importance DESC LIMIT 50"

        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_info(self) -> Dict:
        """DB 정보 조회"""
        info = {}

        # 프로젝트 정보
        project = self.get_project()
        info['project'] = project

        # 파일 통계
        cursor = self.conn.execute("""
            SELECT file_type, COUNT(*) as count, SUM(file_size) as total_size
            FROM source_files
            GROUP BY file_type
        """)
        info['files_by_type'] = [dict(row) for row in cursor.fetchall()]

        # 전체 파일 수
        cursor = self.conn.execute("SELECT COUNT(*) FROM source_files")
        info['total_files'] = cursor.fetchone()[0]

        # 청크 수
        cursor = self.conn.execute("SELECT COUNT(*) FROM content_chunks")
        info['total_chunks'] = cursor.fetchone()[0]

        # 인사이트 수
        cursor = self.conn.execute("""
            SELECT insight_type, COUNT(*) as count
            FROM key_insights
            GROUP BY insight_type
        """)
        info['insights_by_type'] = [dict(row) for row in cursor.fetchall()]

        return info

    def get_files(self) -> List[Dict]:
        """파일 목록 조회"""
        cursor = self.conn.execute("""
            SELECT id, file_name, file_type, file_size, status, processed_at
            FROM source_files
            ORDER BY id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_summary(self) -> List[Dict]:
        """요약 조회"""
        cursor = self.conn.execute("""
            SELECT ki.content, sf.file_name
            FROM key_insights ki
            JOIN source_files sf ON ki.file_id = sf.id
            WHERE ki.insight_type = 'summary'
            ORDER BY ki.importance DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


# ============================================
# LLM 추출기 클래스
# ============================================

class LLMExtractor:
    """LLM 기반 핵심 추출"""

    PROMPT_TEMPLATE = """당신은 문서 분석 전문가입니다. 아래 텍스트에서 핵심 내용을 추출하세요.

[추출 항목]
1. summary: 3-5문장 요약 (전체 맥락 파악용)
2. key_point: 핵심 포인트 (최대 5개, 가장 중요한 논점)
3. fact: 수치, 날짜, 통계 등 사실 정보
4. definition: 새로운 개념이나 용어 정의
5. recommendation: 행동 제안이나 권고사항

[중요도 기준]
- 5: 핵심 주장, 결론, 주요 데이터
- 4: 주요 논거, 중요 세부사항
- 3: 일반적 설명, 배경 정보
- 2: 부가 설명, 예시
- 1: 참고 정보, 각주 수준

[출력 형식]
반드시 아래 JSON 배열 형식으로만 응답하세요:
[
  {{"type": "summary", "content": "요약 내용", "importance": 5, "keywords": ["키워드1", "키워드2"]}},
  {{"type": "key_point", "content": "핵심 포인트", "importance": 4, "keywords": ["키워드"]}},
  ...
]

[분석할 텍스트]
{content}"""

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')

    def extract(self, content: str) -> List[Insight]:
        """텍스트에서 핵심 추출"""
        if not self.api_key:
            return self._pattern_extract(content)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": self.PROMPT_TEMPLATE.format(content=content[:4000])
                }]
            )

            response_text = message.content[0].text

            # JSON 추출
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                insights_data = json.loads(json_match.group())
                return [
                    Insight(
                        insight_type=item.get('type', 'key_point'),
                        content=item.get('content', ''),
                        importance=item.get('importance', 3),
                        keywords=item.get('keywords', [])
                    )
                    for item in insights_data
                ]
        except Exception as e:
            print(f"LLM 추출 오류: {e}, 패턴 기반 추출로 대체")

        return self._pattern_extract(content)

    def _pattern_extract(self, content: str) -> List[Insight]:
        """패턴 기반 핵심 추출 (LLM 대체)"""
        insights = []

        # 요약 (첫 2-3 문장)
        sentences = re.split(r'[.!?]\s+', content)
        if sentences:
            summary = '. '.join(sentences[:3]) + '.'
            insights.append(Insight(
                insight_type='summary',
                content=summary[:500],
                importance=4
            ))

        # 정의 패턴: ~란, ~은 ~이다
        def_patterns = [
            r'(.{5,50})(이?란|은|는)\s+(.{10,200})(이다|입니다)[.]',
            r'(.{5,50}):\s*(.{10,200})[.]'
        ]
        for pattern in def_patterns:
            for match in re.finditer(pattern, content):
                insights.append(Insight(
                    insight_type='definition',
                    content=match.group(0)[:300],
                    importance=3
                ))

        # 사실 패턴: 숫자 포함 문장
        fact_pattern = r'[^.]*\d+[%억만천원년월일개명건회]+[^.]*[.]'
        for match in re.finditer(fact_pattern, content):
            if len(match.group(0)) > 20:
                insights.append(Insight(
                    insight_type='fact',
                    content=match.group(0)[:300],
                    importance=4
                ))

        # 권고 패턴: ~해야, ~필요
        rec_patterns = [
            r'[^.]*해야\s*(한다|합니다)[^.]*[.]',
            r'[^.]*필요(하다|합니다|가 있다)[^.]*[.]',
            r'[^.]*권장[^.]*[.]'
        ]
        for pattern in rec_patterns:
            for match in re.finditer(pattern, content):
                insights.append(Insight(
                    insight_type='recommendation',
                    content=match.group(0)[:300],
                    importance=3
                ))

        return insights[:20]  # 최대 20개


# ============================================
# CLI 함수
# ============================================

def cmd_import(args):
    """파일 임포트 명령"""
    db_path = Path(args.db_path)

    # DB 디렉토리 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(db_path)
    db.connect()
    db.init_schema()

    # 프로젝트 생성/조회
    project = db.get_project()
    if not project:
        project_name = args.name or db_path.stem
        project_id = db.create_project(project_name, args.purpose)
        print(f"프로젝트 생성: {project_name}")
    else:
        project_id = project['id']
        print(f"기존 프로젝트 사용: {project['name']}")

    # 파서 초기화
    parsers = {
        'md': MarkdownParser(),
        'txt': TextParser(),
        'csv': CsvParser(),
        'db': DbParser(),
        'pdf': PdfParser()
    }

    # 파일 처리
    for file_arg in args.files:
        file_path = Path(file_arg)

        if not file_path.exists():
            print(f"파일 없음: {file_path}")
            continue

        ext = file_path.suffix.lower().lstrip('.')
        if f'.{ext}' not in SUPPORTED_EXTENSIONS:
            print(f"지원하지 않는 형식: {file_path}")
            continue

        print(f"\n처리 중: {file_path.name}")

        try:
            file_id = db.add_file(project_id, file_path)

            parser = parsers.get(ext)
            if not parser:
                continue

            # 파싱
            if ext == 'csv':
                chunks, structured = parser.parse(file_path)
                db.save_chunks(file_id, chunks)
                if structured:
                    db.save_structured_data(file_id, file_path.stem, structured)
            elif ext == 'db':
                chunks, tables_info = parser.parse(file_path)
                db.save_chunks(file_id, chunks)
                if tables_info:
                    db.save_db_table_info(file_id, tables_info)
            else:
                chunks = parser.parse(file_path)
                db.save_chunks(file_id, chunks)

            db.update_file_status(file_id, 'processed')
            print(f"  -> {len(chunks)}개 청크 저장")

        except Exception as e:
            db.update_file_status(file_id, 'error', str(e))
            print(f"  -> 오류: {e}")

    db.close()
    print(f"\n완료: {format_path(str(db_path))}")


def cmd_extract(args):
    """LLM 핵심 추출 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    extractor = LLMExtractor()

    file_id = args.file_id if hasattr(args, 'file_id') else None
    chunks = db.get_chunks_for_extraction(file_id)

    if not chunks:
        print("추출할 청크가 없습니다.")
        db.close()
        return

    print(f"추출 대상: {len(chunks)}개 청크")

    for i, chunk in enumerate(chunks):
        print(f"\n[{i+1}/{len(chunks)}] {chunk['file_name']} - {chunk.get('title', '(제목없음)')}")

        insights = extractor.extract(chunk['content'])

        if insights:
            db.save_insights(chunk['file_id'], chunk['id'], insights)
            print(f"  -> {len(insights)}개 인사이트 추출")
        else:
            print("  -> 추출된 인사이트 없음")

    db.close()
    print("\n추출 완료")


def cmd_info(args):
    """DB 정보 조회 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    info = db.get_info()

    print("=" * 50)
    print("study2db 정보")
    print("=" * 50)

    if info['project']:
        print(f"\n[프로젝트]")
        print(f"  이름: {info['project']['name']}")
        print(f"  목적: {info['project'].get('purpose', '-')}")
        print(f"  생성: {info['project'].get('created_at', '-')}")

    print(f"\n[파일]")
    print(f"  총 파일 수: {info['total_files']}")
    for ft in info['files_by_type']:
        size_kb = (ft['total_size'] or 0) / 1024
        print(f"  - {ft['file_type']}: {ft['count']}개 ({size_kb:.1f}KB)")

    print(f"\n[콘텐츠]")
    print(f"  총 청크 수: {info['total_chunks']}")

    print(f"\n[인사이트]")
    for it in info['insights_by_type']:
        print(f"  - {it['insight_type']}: {it['count']}개")

    db.close()


def cmd_files(args):
    """파일 목록 조회 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    files = db.get_files()

    print(f"\n{'ID':>4} {'상태':>10} {'유형':>6} {'크기':>10} {'파일명'}")
    print("-" * 60)

    for f in files:
        size_str = f"{f['file_size']/1024:.1f}KB" if f['file_size'] else "-"
        print(f"{f['id']:>4} {f['status']:>10} {f['file_type']:>6} {size_str:>10} {f['file_name']}")

    db.close()


def cmd_summary(args):
    """요약 조회 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    summaries = db.get_summary()

    if not summaries:
        print("저장된 요약이 없습니다. extract 명령을 실행하세요.")
        db.close()
        return

    print("\n" + "=" * 50)
    print("파일별 요약")
    print("=" * 50)

    for s in summaries:
        print(f"\n[{s['file_name']}]")
        print(s['content'][:500])

    db.close()


def cmd_search(args):
    """검색 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    results = db.search(
        args.query,
        insight_type=args.type if hasattr(args, 'type') else None,
        importance=args.importance if hasattr(args, 'importance') else None
    )

    if not results:
        print("검색 결과 없음")
        db.close()
        return

    print(f"\n검색 결과: {len(results)}건")
    print("=" * 50)

    for i, r in enumerate(results[:20]):
        print(f"\n[{i+1}] {r['insight_type']} (중요도: {r['importance']})")
        print(f"    출처: {r['file_name']}")
        if r.get('source_section'):
            print(f"    섹션: {r['source_section']}")
        print(f"    내용: {r['content'][:200]}...")

    db.close()


def cmd_migrate(args):
    """마이그레이션 명령"""
    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"DB 없음: {db_path}")
        return

    db = DatabaseManager(db_path)
    db.connect()

    # 현재 버전 확인
    current_version = db.get_schema_version()
    print(f"현재 스키마 버전: v{current_version}")
    print(f"최신 스키마 버전: v{SCHEMA_VERSION}")

    if current_version >= SCHEMA_VERSION:
        print("\n이미 최신 버전입니다. 마이그레이션이 필요하지 않습니다.")
        db.close()
        return

    # 마이그레이션 실행
    create_backup = not args.no_backup if hasattr(args, 'no_backup') else True
    result = db.migrate(create_backup=create_backup)

    print(f"\n{result['message']}")
    if result.get('backup_path'):
        print(f"백업 파일: {result['backup_path']}")

    db.close()


# ============================================
# 메인
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='study2db - 학습 자료 통합 DB 변환기',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='명령어')

    # import 명령
    import_parser = subparsers.add_parser('import', help='파일 임포트')
    import_parser.add_argument('db_path', help='출력 DB 경로')
    import_parser.add_argument('files', nargs='+', help='입력 파일들')
    import_parser.add_argument('--name', '-n', help='프로젝트명')
    import_parser.add_argument('--purpose', '-p', help='분석 목적')

    # extract 명령
    extract_parser = subparsers.add_parser('extract', help='LLM 핵심 추출')
    extract_parser.add_argument('db_path', help='DB 경로')
    extract_parser.add_argument('--file-id', '-f', type=int, help='특정 파일 ID만 처리')

    # info 명령
    info_parser = subparsers.add_parser('info', help='DB 정보 조회')
    info_parser.add_argument('db_path', help='DB 경로')

    # files 명령
    files_parser = subparsers.add_parser('files', help='파일 목록 조회')
    files_parser.add_argument('db_path', help='DB 경로')

    # summary 명령
    summary_parser = subparsers.add_parser('summary', help='요약 조회')
    summary_parser.add_argument('db_path', help='DB 경로')

    # search 명령
    search_parser = subparsers.add_parser('search', help='검색')
    search_parser.add_argument('db_path', help='DB 경로')
    search_parser.add_argument('query', help='검색어')
    search_parser.add_argument('--type', '-t', choices=['summary', 'key_point', 'definition', 'fact', 'recommendation'])
    search_parser.add_argument('--importance', '-i', type=int, choices=[1,2,3,4,5])

    # migrate 명령
    migrate_parser = subparsers.add_parser('migrate', help='스키마 마이그레이션 (v1 → v2)')
    migrate_parser.add_argument('db_path', help='DB 경로')
    migrate_parser.add_argument('--no-backup', action='store_true', help='백업 생성 안함')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'import': cmd_import,
        'extract': cmd_extract,
        'info': cmd_info,
        'files': cmd_files,
        'summary': cmd_summary,
        'search': cmd_search,
        'migrate': cmd_migrate
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)


if __name__ == '__main__':
    main()
