-- ============================================
-- study2db Schema v2
-- 학습 자료 통합 DB 스키마
-- ============================================

PRAGMA encoding = 'UTF-8';
PRAGMA foreign_keys = ON;

-- ============================================
-- 0. 스키마 버전 관리
-- ============================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now', 'localtime')),
    description TEXT
);

-- 초기 버전 삽입 (새 DB 생성 시)
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (2, 'v1.1.0 - 스키마 버전 관리 도입, YAML 파싱 고도화');

-- ============================================
-- 1. 스터디 프로젝트 (루트)
-- ============================================
CREATE TABLE IF NOT EXISTS study_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 스터디/프로젝트명
    purpose TEXT,                          -- 분석 목적 (보고서 작성 주제)
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT
);

-- ============================================
-- 2. 원본 파일 정보
-- ============================================
CREATE TABLE IF NOT EXISTS source_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,               -- 원본 파일 절대경로
    file_name TEXT NOT NULL,               -- 파일명
    file_type TEXT NOT NULL,               -- md, txt, csv, db, pdf
    file_size INTEGER,                     -- 바이트
    file_hash TEXT,                        -- SHA256 해시 (중복 방지)
    encoding TEXT DEFAULT 'utf-8',
    processed_at TEXT,
    status TEXT DEFAULT 'pending',         -- pending, processed, error
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES study_projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, file_hash)
);

CREATE INDEX IF NOT EXISTS idx_files_project ON source_files(project_id);
CREATE INDEX IF NOT EXISTS idx_files_type ON source_files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_status ON source_files(status);

-- ============================================
-- 3. 콘텐츠 청크 (원본 텍스트)
-- ============================================
CREATE TABLE IF NOT EXISTS content_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,          -- 파일 내 순서 (0부터)
    chunk_type TEXT NOT NULL,              -- section, paragraph, table, code, list, frontmatter
    title TEXT,                            -- 섹션/챕터 제목 (있는 경우)
    content TEXT NOT NULL,                 -- 텍스트 내용
    word_count INTEGER,                    -- 단어 수
    start_line INTEGER,                    -- 원본 시작 줄 번호
    end_line INTEGER,                      -- 원본 끝 줄 번호
    metadata TEXT,                         -- JSON (level, path 등 추가 정보)
    FOREIGN KEY (file_id) REFERENCES source_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_file ON content_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON content_chunks(chunk_type);

-- ============================================
-- 4. 핵심 내용 (LLM 추출)
-- ============================================
CREATE TABLE IF NOT EXISTS key_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER,                      -- 원본 청크 (NULL: 파일 전체 요약)
    file_id INTEGER NOT NULL,
    insight_type TEXT NOT NULL,            -- summary, key_point, definition, fact, recommendation
    content TEXT NOT NULL,                 -- 핵심 내용
    importance INTEGER DEFAULT 3,          -- 1-5 (5가 가장 중요)
    keywords TEXT,                         -- JSON 배열 ["키워드1", "키워드2"]
    extracted_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (chunk_id) REFERENCES content_chunks(id) ON DELETE SET NULL,
    FOREIGN KEY (file_id) REFERENCES source_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_insights_file ON key_insights(file_id);
CREATE INDEX IF NOT EXISTS idx_insights_chunk ON key_insights(chunk_id);
CREATE INDEX IF NOT EXISTS idx_insights_type ON key_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_insights_importance ON key_insights(importance);

-- ============================================
-- 5. 구조화 데이터 (CSV, 테이블)
-- ============================================
CREATE TABLE IF NOT EXISTS structured_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    table_name TEXT,                       -- 원본 테이블/시트명
    row_index INTEGER NOT NULL,            -- 행 번호 (0부터)
    data_json TEXT NOT NULL,               -- JSON 객체 {"열명": "값", ...}
    FOREIGN KEY (file_id) REFERENCES source_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_structured_file ON structured_data(file_id);
CREATE INDEX IF NOT EXISTS idx_structured_table ON structured_data(table_name);

-- ============================================
-- 6. 외부 DB 테이블 참조
-- ============================================
CREATE TABLE IF NOT EXISTS external_db_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    original_table TEXT NOT NULL,          -- 원본 DB 테이블명
    imported_table TEXT NOT NULL,          -- study DB에 복제된 테이블명 (ext_*)
    row_count INTEGER,
    schema_json TEXT,                      -- 컬럼 정보 JSON [{"name": "col", "type": "TEXT"}, ...]
    FOREIGN KEY (file_id) REFERENCES source_files(id) ON DELETE CASCADE
);

-- ============================================
-- 7. 전문 검색 (FTS5)
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
    title,
    content,
    content=content_chunks,
    content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts USING fts5(
    content,
    keywords,
    content=key_insights,
    content_rowid=id
);

-- FTS 동기화 트리거: content_chunks
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON content_chunks BEGIN
    INSERT INTO content_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON content_chunks BEGIN
    INSERT INTO content_fts(content_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON content_chunks BEGIN
    INSERT INTO content_fts(content_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
    INSERT INTO content_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
END;

-- FTS 동기화 트리거: key_insights
CREATE TRIGGER IF NOT EXISTS insights_ai AFTER INSERT ON key_insights BEGIN
    INSERT INTO insights_fts(rowid, content, keywords)
    VALUES (new.id, new.content, new.keywords);
END;

CREATE TRIGGER IF NOT EXISTS insights_ad AFTER DELETE ON key_insights BEGIN
    INSERT INTO insights_fts(insights_fts, rowid, content, keywords)
    VALUES ('delete', old.id, old.content, old.keywords);
END;

CREATE TRIGGER IF NOT EXISTS insights_au AFTER UPDATE ON key_insights BEGIN
    INSERT INTO insights_fts(insights_fts, rowid, content, keywords)
    VALUES ('delete', old.id, old.content, old.keywords);
    INSERT INTO insights_fts(rowid, content, keywords)
    VALUES (new.id, new.content, new.keywords);
END;

-- ============================================
-- 유용한 쿼리 예시
-- ============================================

/*
-- 1. 프로젝트별 파일 현황
SELECT sp.name, sf.file_name, sf.file_type, sf.status
FROM study_projects sp
JOIN source_files sf ON sp.id = sf.project_id;

-- 2. 핵심 포인트 조회 (중요도 4 이상)
SELECT ki.content, ki.importance, sf.file_name
FROM key_insights ki
JOIN source_files sf ON ki.file_id = sf.id
WHERE ki.insight_type = 'key_point' AND ki.importance >= 4
ORDER BY ki.importance DESC;

-- 3. 정의 목록 (용어집)
SELECT content, keywords FROM key_insights
WHERE insight_type = 'definition'
ORDER BY extracted_at;

-- 4. 사실/데이터 검색 (근거 자료)
SELECT ki.content, sf.file_name, cc.title as source_section
FROM key_insights ki
JOIN source_files sf ON ki.file_id = sf.id
LEFT JOIN content_chunks cc ON ki.chunk_id = cc.id
WHERE ki.insight_type = 'fact';

-- 5. 전문 검색 (FTS5)
SELECT cc.title, cc.content, sf.file_name
FROM content_fts fts
JOIN content_chunks cc ON fts.rowid = cc.id
JOIN source_files sf ON cc.file_id = sf.id
WHERE content_fts MATCH '디지털 전환';

-- 6. 인사이트 전문 검색
SELECT ki.content, ki.insight_type, sf.file_name
FROM insights_fts fts
JOIN key_insights ki ON fts.rowid = ki.id
JOIN source_files sf ON ki.file_id = sf.id
WHERE insights_fts MATCH '전략';

-- 7. 파일별 요약 조회
SELECT sf.file_name, ki.content as summary
FROM key_insights ki
JOIN source_files sf ON ki.file_id = sf.id
WHERE ki.insight_type = 'summary' AND ki.chunk_id IS NULL;

-- 8. CSV 데이터 조회 (JSON 추출)
SELECT
    json_extract(data_json, '$.컬럼명') as value,
    file_id
FROM structured_data
WHERE table_name = '테이블명';
*/
