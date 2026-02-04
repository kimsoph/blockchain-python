# -*- coding: utf-8 -*-
"""
Database schema definitions for md2db v2

v2 스키마 주요 변경:
- source_files: 원본 파일 추적 (SHA256 해시, 중복/변경 감지)
- frontmatter: 프론트매터 분리 저장 (YAML 고도화)
- tags + document_tags: 태그 정규화 (N:M)
- block_metadata: 블록별 상세 메타 (EAV)
- table_columns: 테이블 열 정보
- chroma_sync: ChromaDB 동기화 상태
- schema_version: 마이그레이션 지원
"""

SCHEMA_VERSION = 2

SCHEMA_V2 = """
-- ============================================================
-- md2db v2 스키마 정의
-- ============================================================

PRAGMA encoding = 'UTF-8';
PRAGMA foreign_keys = ON;

-- 스키마 버전 관리
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now', 'localtime')),
    description TEXT
);

-- ============================================================
-- 원본 파일 추적 (증분 동기화 핵심)
-- ============================================================
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
);

-- ============================================================
-- 문서 메타데이터
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER,
    filename TEXT NOT NULL,
    title TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    file_size INTEGER,
    total_sections INTEGER,
    total_blocks INTEGER,
    total_words INTEGER DEFAULT 0,
    encoding TEXT DEFAULT 'utf-8',
    FOREIGN KEY (source_file_id) REFERENCES source_files(id) ON DELETE SET NULL
);

-- ============================================================
-- 프론트매터 (YAML 고도화)
-- ============================================================
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
    period TEXT,
    aliases TEXT,
    cssclass TEXT,
    tags_json TEXT,
    custom_fields TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- ============================================================
-- 태그 (정규화)
-- ============================================================
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS document_tags (
    document_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (document_id, tag_id),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- ============================================================
-- 섹션 (헤더 기반 계층 구조)
-- ============================================================
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    parent_id INTEGER,
    level INTEGER NOT NULL
        CHECK (level >= 0 AND level <= 6),
    title TEXT,
    path TEXT,
    position INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    word_count INTEGER DEFAULT 0,
    has_subsections INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES sections(id) ON DELETE SET NULL
);

-- ============================================================
-- 콘텐츠 블록
-- ============================================================
CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    type TEXT NOT NULL
        CHECK (type IN (
            'frontmatter', 'header', 'paragraph', 'list',
            'code_block', 'blockquote', 'table',
            'horizontal_rule', 'image', 'callout',
            'math_block', 'mermaid', 'empty'
        )),
    content TEXT,
    raw_markdown TEXT,
    position INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,
    metadata TEXT,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
);

-- ============================================================
-- 블록 상세 메타데이터 (EAV 패턴)
-- ============================================================
CREATE TABLE IF NOT EXISTS block_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE,
    UNIQUE (block_id, key)
);

-- ============================================================
-- 테이블 열 정보
-- ============================================================
CREATE TABLE IF NOT EXISTS table_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    header_text TEXT,
    data_type TEXT,
    alignment TEXT DEFAULT 'left'
        CHECK (alignment IN ('left', 'center', 'right')),
    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
);

-- ============================================================
-- ChromaDB 동기화 상태
-- ============================================================
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
);

-- ============================================================
-- 인덱스
-- ============================================================

-- source_files 인덱스
CREATE INDEX IF NOT EXISTS idx_source_files_hash ON source_files(file_hash);
CREATE INDEX IF NOT EXISTS idx_source_files_path ON source_files(file_path);
CREATE INDEX IF NOT EXISTS idx_source_files_status ON source_files(status);

-- documents 인덱스
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_file_id);
CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title);

-- frontmatter 인덱스
CREATE INDEX IF NOT EXISTS idx_frontmatter_doc ON frontmatter(document_id);
CREATE INDEX IF NOT EXISTS idx_frontmatter_author ON frontmatter(author);
CREATE INDEX IF NOT EXISTS idx_frontmatter_type ON frontmatter(type);
CREATE INDEX IF NOT EXISTS idx_frontmatter_period ON frontmatter(period);

-- sections 인덱스
CREATE INDEX IF NOT EXISTS idx_sections_document ON sections(document_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_id);
CREATE INDEX IF NOT EXISTS idx_sections_path ON sections(path);
CREATE INDEX IF NOT EXISTS idx_sections_level ON sections(level);

-- blocks 인덱스
CREATE INDEX IF NOT EXISTS idx_blocks_section ON blocks(section_id);
CREATE INDEX IF NOT EXISTS idx_blocks_type ON blocks(type);

-- chroma_sync 인덱스
CREATE INDEX IF NOT EXISTS idx_chroma_doc ON chroma_sync(document_id);
CREATE INDEX IF NOT EXISTS idx_chroma_status ON chroma_sync(status);
"""

FTS_SCHEMA = """
-- ============================================================
-- 전문 검색 (FTS5)
-- ============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts USING fts5(
    content,
    raw_markdown,
    content=blocks,
    content_rowid=id,
    tokenize='unicode61 remove_diacritics 2'
);

-- FTS 트리거
CREATE TRIGGER IF NOT EXISTS blocks_ai AFTER INSERT ON blocks BEGIN
    INSERT INTO blocks_fts(rowid, content, raw_markdown)
    VALUES (new.id, new.content, new.raw_markdown);
END;

CREATE TRIGGER IF NOT EXISTS blocks_ad AFTER DELETE ON blocks BEGIN
    INSERT INTO blocks_fts(blocks_fts, rowid, content, raw_markdown)
    VALUES('delete', old.id, old.content, old.raw_markdown);
END;

CREATE TRIGGER IF NOT EXISTS blocks_au AFTER UPDATE ON blocks BEGIN
    INSERT INTO blocks_fts(blocks_fts, rowid, content, raw_markdown)
    VALUES('delete', old.id, old.content, old.raw_markdown);
    INSERT INTO blocks_fts(rowid, content, raw_markdown)
    VALUES (new.id, new.content, new.raw_markdown);
END;
"""

# v1 스키마 (하위 호환성용)
SCHEMA_V1 = """
-- 문서 메타데이터 (v1)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    title TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER,
    total_sections INTEGER,
    total_blocks INTEGER,
    encoding TEXT DEFAULT 'utf-8',
    frontmatter TEXT
);

-- 섹션 (v1)
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    title TEXT,
    path TEXT,
    position INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    parent_id INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 블록 (v1)
CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    content TEXT,
    raw_markdown TEXT,
    position INTEGER NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    metadata TEXT,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
);

-- 인덱스 (v1)
CREATE INDEX IF NOT EXISTS idx_sections_document ON sections(document_id);
CREATE INDEX IF NOT EXISTS idx_sections_level ON sections(level);
CREATE INDEX IF NOT EXISTS idx_sections_path ON sections(path);
CREATE INDEX IF NOT EXISTS idx_blocks_section ON blocks(section_id);
CREATE INDEX IF NOT EXISTS idx_blocks_type ON blocks(type);
"""
