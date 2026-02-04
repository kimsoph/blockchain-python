# Markdown2DB Schema Reference

마크다운을 SQLite DB로 변환할 때 사용되는 스키마 정의 문서입니다.

## ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│    documents    │
├─────────────────┤
│ id (PK)         │
│ filename        │
│ title           │
│ created_at      │
│ file_size       │
│ total_sections  │
│ total_blocks    │
│ encoding        │
│ frontmatter     │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│    sections     │
├─────────────────┤
│ id (PK)         │
│ document_id (FK)│───┐
│ level           │   │
│ title           │   │ self-reference
│ path            │   │ (parent-child)
│ position        │   │
│ start_line      │   │
│ end_line        │   │
│ parent_id (FK)  │◄──┘
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│     blocks      │
├─────────────────┤
│ id (PK)         │
│ section_id (FK) │
│ type            │
│ content         │
│ raw_markdown    │
│ position        │
│ start_line      │
│ end_line        │
│ metadata        │
└─────────────────┘
         │
         ▼ (FTS5)
┌─────────────────┐
│   blocks_fts    │
├─────────────────┤
│ content         │
│ raw_markdown    │
└─────────────────┘
```

## 테이블 상세

### documents (문서 메타데이터)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | INTEGER PK | 문서 고유 ID | 1 |
| `filename` | TEXT NOT NULL | 파일명 | "document.md" |
| `title` | TEXT | 문서 제목 | "IBK 60년사" |
| `created_at` | TEXT | 생성 시각 | "2025-12-18 10:30:00" |
| `file_size` | INTEGER | 파일 크기 (bytes) | 824576 |
| `total_sections` | INTEGER | 총 섹션 수 | 45 |
| `total_blocks` | INTEGER | 총 블록 수 | 320 |
| `encoding` | TEXT | 인코딩 | "utf-8" |
| `frontmatter` | TEXT | YAML 프론트매터 (JSON) | '{"title": "...", "date": "..."}' |

```sql
CREATE TABLE documents (
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
```

### sections (헤더 기반 섹션)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | INTEGER PK | 섹션 고유 ID | 1 |
| `document_id` | INTEGER FK | 문서 ID | 1 |
| `level` | INTEGER | 헤더 레벨 (0=루트, 1-6) | 2 |
| `title` | TEXT | 헤더 텍스트 | "CHAPTER 1" |
| `path` | TEXT | 계층 경로 | "1.2.3" |
| `position` | INTEGER | 문서 내 순서 | 5 |
| `start_line` | INTEGER | 시작 줄 번호 | 45 |
| `end_line` | INTEGER | 끝 줄 번호 | 120 |
| `parent_id` | INTEGER FK | 부모 섹션 ID | 2 |

```sql
CREATE TABLE sections (
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
```

#### path 필드 설명

`path`는 섹션의 계층 구조를 나타내는 문자열입니다:

```
# Part 1        → path: "1"
## Chapter 1    → path: "1.1"
### Section 1   → path: "1.1.1"
### Section 2   → path: "1.1.2"
## Chapter 2    → path: "1.2"
# Part 2        → path: "2"
## Chapter 1    → path: "2.1"
```

이 구조를 통해:
- 특정 섹션 조회: `WHERE path = '1.2'`
- 하위 섹션 포함 조회: `WHERE path LIKE '1.2%'`
- 트리 구조 재구성 가능

### blocks (콘텐츠 블록)

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | INTEGER PK | 블록 고유 ID | 1 |
| `section_id` | INTEGER FK | 섹션 ID | 5 |
| `type` | TEXT | 블록 유형 | "paragraph" |
| `content` | TEXT | 텍스트 내용 (마크다운 제거) | "본문 텍스트입니다." |
| `raw_markdown` | TEXT | 원본 마크다운 | "**본문** 텍스트입니다." |
| `position` | INTEGER | 섹션 내 순서 | 3 |
| `start_line` | INTEGER | 시작 줄 번호 | 50 |
| `end_line` | INTEGER | 끝 줄 번호 | 55 |
| `metadata` | TEXT | 추가 메타데이터 (JSON) | '{"language": "python"}' |

```sql
CREATE TABLE blocks (
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
```

#### type 필드 값

| 타입 | 설명 | metadata 예시 |
|------|------|---------------|
| `frontmatter` | YAML 프론트매터 | - |
| `header` | 헤더 | `{"level": 2}` |
| `paragraph` | 일반 단락 | - |
| `list` | 리스트 | - |
| `code_block` | 코드 블록 | `{"language": "python", "fence": "```"}` |
| `blockquote` | 인용구 | - |
| `table` | 테이블 | - |
| `horizontal_rule` | 수평선 | - |
| `image` | 이미지 | `{"alt": "설명", "src": "image.png"}` |

### blocks_fts (전문 검색)

FTS5 가상 테이블로 `content`와 `raw_markdown` 필드의 전문 검색을 지원합니다.

```sql
CREATE VIRTUAL TABLE blocks_fts USING fts5(
    content,
    raw_markdown,
    content=blocks,
    content_rowid=id
);
```

## 인덱스

```sql
-- 문서별 섹션 조회 최적화
CREATE INDEX idx_sections_document ON sections(document_id);

-- 레벨별 섹션 필터링
CREATE INDEX idx_sections_level ON sections(level);

-- 경로 기반 섹션 조회
CREATE INDEX idx_sections_path ON sections(path);

-- 섹션별 블록 조회 최적화
CREATE INDEX idx_blocks_section ON blocks(section_id);

-- 블록 타입별 필터링
CREATE INDEX idx_blocks_type ON blocks(type);
```

## 유용한 쿼리 예시

### 문서 통계

```sql
-- 문서별 섹션/블록 수
SELECT
    d.filename,
    d.title,
    COUNT(DISTINCT s.id) as section_count,
    COUNT(b.id) as block_count
FROM documents d
LEFT JOIN sections s ON d.id = s.document_id
LEFT JOIN blocks b ON s.id = b.section_id
GROUP BY d.id;
```

### 섹션 트리 조회

```sql
-- 특정 문서의 섹션 트리 (들여쓰기 포함)
SELECT
    printf('%s%s', substr('                    ', 1, level * 2), title) as tree,
    path,
    (end_line - start_line + 1) as lines
FROM sections
WHERE document_id = 1 AND level > 0
ORDER BY position;
```

### 가장 긴 블록 찾기

```sql
-- 가장 긴 단락 상위 10개
SELECT
    s.title as section,
    LENGTH(b.content) as length,
    SUBSTR(b.content, 1, 100) as preview
FROM blocks b
JOIN sections s ON b.section_id = s.id
WHERE b.type = 'paragraph'
ORDER BY LENGTH(b.content) DESC
LIMIT 10;
```

### 전문 검색

```sql
-- FTS5 검색 (하이라이트 포함)
SELECT
    s.path,
    s.title,
    highlight(blocks_fts, 0, '<mark>', '</mark>') as matched_content
FROM blocks_fts
JOIN blocks b ON blocks_fts.rowid = b.id
JOIN sections s ON b.section_id = s.id
WHERE blocks_fts MATCH '디지털 OR 혁신'
LIMIT 20;
```

### 섹션별 콘텐츠 재조합

```sql
-- 특정 섹션의 모든 콘텐츠 (마크다운 복원용)
SELECT raw_markdown
FROM blocks
WHERE section_id IN (
    SELECT id FROM sections
    WHERE path = '2.1' OR path LIKE '2.1.%'
)
ORDER BY section_id, position;
```

## 데이터 무결성

### CASCADE 삭제

문서 삭제 시 관련 섹션과 블록이 자동 삭제됩니다:

```sql
DELETE FROM documents WHERE id = 1;
-- → sections, blocks도 자동 삭제
```

### 트리거 (FTS 동기화)

블록 CUD 작업 시 FTS 테이블 자동 동기화:

```sql
-- INSERT 트리거
CREATE TRIGGER blocks_ai AFTER INSERT ON blocks BEGIN
    INSERT INTO blocks_fts(rowid, content, raw_markdown)
    VALUES (new.id, new.content, new.raw_markdown);
END;

-- DELETE 트리거
CREATE TRIGGER blocks_ad AFTER DELETE ON blocks BEGIN
    INSERT INTO blocks_fts(blocks_fts, rowid, content, raw_markdown)
    VALUES('delete', old.id, old.content, old.raw_markdown);
END;

-- UPDATE 트리거
CREATE TRIGGER blocks_au AFTER UPDATE ON blocks BEGIN
    INSERT INTO blocks_fts(blocks_fts, rowid, content, raw_markdown)
    VALUES('delete', old.id, old.content, old.raw_markdown);
    INSERT INTO blocks_fts(rowid, content, raw_markdown)
    VALUES (new.id, new.content, new.raw_markdown);
END;
```

## 마이그레이션 고려사항

### 스키마 버전 관리

향후 스키마 변경 시 마이그레이션을 위해 버전 테이블 추가 권장:

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO schema_version (version) VALUES (1);
```

### 하위 호환성

- `frontmatter` 컬럼: NULL 허용 (기존 문서 호환)
- `metadata` 컬럼: NULL 허용 (선택적 확장)
- FTS 테이블: 미지원 환경에서도 기본 기능 동작
