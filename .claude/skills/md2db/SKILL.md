---
name: md2db
description: 마크다운 파일을 SQLite DB로 파싱하여 저장하는 스킬. 헤더 기반 섹션 계층 구조와 블록 단위 콘텐츠를 분리 저장하여 대용량 문서의 효율적 처리를 지원. v2에서 YAML 파싱 고도화, 파일 중복/변경 감지, ChromaDB 통합 기능 추가.
version: 2.0.0
---

# Markdown to Database Skill

## Purpose

이 스킬은 대용량 마크다운 파일을 SQLite DB로 변환하여 저장합니다. Context/토큰 한계를 극복하고 문서 처리(클리닝, 요약, 재구성 등)를 효율적으로 수행할 수 있습니다.

**핵심 기능:**
1. 마크다운 파싱 → SQLite DB 생성
2. 헤더 기반 섹션 계층 구조 유지
3. 블록 단위(단락, 리스트, 코드 블록 등) 분리
4. DB에서 마크다운으로 복원
5. **v2 신규:** ChromaDB 벡터 DB 변환 (`--to-chroma`)
6. **v2 신규:** 파일 중복/변경 감지 (SHA256 해시)
7. **v2 신규:** YAML 프론트매터 고도화 (PyYAML)

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 대용량 마크다운 파일을 분할 처리해야 할 때
- 문서의 특정 섹션만 추출하거나 수정할 때
- 문서 구조를 분석하거나 재구성할 때
- 여러 문서를 통합 관리해야 할 때
- **v2:** 의미 기반 검색이 필요할 때 (ChromaDB)
- **v2:** 파일 변경을 추적하고 증분 업데이트할 때

트리거 예시:
- "이 마크다운 파일을 DB로 변환해줘"
- "문서를 섹션별로 분리해서 저장해줘"
- "DB에서 2장 내용만 마크다운으로 추출해줘"
- **v2:** "DB를 ChromaDB로 변환해줘"
- **v2:** "기존 DB를 v2로 마이그레이션해줘"

## Architecture

### DB 스키마 구조 (v2)

```
source_files (원본 파일 추적 - v2 신규)
    ↓
documents (문서 메타데이터)
    ├── frontmatter (프론트매터 - v2 신규 테이블)
    ├── document_tags (태그 연결 - v2 신규)
    └── sections (헤더 기반 계층 구조)
            └── blocks (콘텐츠 블록)
                    └── blocks_fts (전문 검색)

chroma_sync (ChromaDB 동기화 상태 - v2 신규)
```

### 테이블 설명

| 테이블 | 설명 | 주요 필드 |
|--------|------|-----------|
| `source_files` | 원본 파일 추적 (v2) | file_path, file_hash, status |
| `documents` | 문서 메타데이터 | filename, title, total_words |
| `frontmatter` | 프론트매터 (v2.1) | parsed_json, title, author, **period**, tags_json |
| `tags` | 태그 (v2) | tag_name |
| `sections` | 헤더 기반 섹션 | level, title, path, word_count |
| `blocks` | 콘텐츠 블록 | type, content, raw_markdown, word_count |
| `blocks_fts` | 전문 검색 | content, raw_markdown (FTS5) |
| `chroma_sync` | ChromaDB 동기화 (v2) | collection_name, status |

> **v2.1 신규**: `frontmatter.period` 컬럼 추가 - "2025년 11월" → "2025-11" 자동 정규화

### 블록 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `paragraph` | 일반 단락 | 본문 텍스트 |
| `header` | 헤더 | `# 제목`, `## 소제목` |
| `list` | 리스트 전체 | 순서/비순서 리스트 |
| `code_block` | 코드 블록 | ` ```python ... ``` ` |
| `blockquote` | 인용구 | `> 인용문` |
| `table` | 테이블 | `\| 열1 \| 열2 \|` |
| `horizontal_rule` | 수평선 | `---` |
| `frontmatter` | YAML 프론트매터 | `---\ntitle: ...\n---` |
| `image` | 이미지 (v2.1) | `![alt](path)`, `![[path\|size]]` |
| `callout` | Obsidian 콜아웃 (v2) | `> [!note]` |
| `math_block` | 수식 블록 (v2) | `$$...$$` |
| `mermaid` | Mermaid 다이어그램 (v2) | ` ```mermaid ``` ` |

> **v2.1 신규**: Obsidian wikilink 이미지 `![[path|size]]` 지원, metadata에 format/path/size 저장

## Workflow

### Step 1: 마크다운 → DB 변환

```bash
# 기본 변환
python .claude/skills/md2db/scripts/md2db.py input.md output.db

# 기존 DB에 추가
python .claude/skills/md2db/scripts/md2db.py input.md existing.db --append

# 강제 업데이트 (중복 파일도 재처리)
python .claude/skills/md2db/scripts/md2db.py input.md output.db --force-update
```

### Step 2: DB 쿼리로 처리

```bash
# 문서 정보 조회
python .claude/skills/md2db/scripts/md2db.py output.db --info

# 섹션 목록 조회
python .claude/skills/md2db/scripts/md2db.py output.db --sections

# 전문 검색
python .claude/skills/md2db/scripts/md2db.py output.db --search "키워드"
```

### Step 3: DB → 마크다운 복원

```bash
# 전체 문서 복원
python .claude/skills/md2db/scripts/md2db.py output.db --export result.md

# 특정 섹션만 복원
python .claude/skills/md2db/scripts/md2db.py output.db --export result.md --section "2"

# 특정 레벨까지만 복원
python .claude/skills/md2db/scripts/md2db.py output.db --export result.md --max-level 2
```

### Step 4: ChromaDB 변환 (v2 신규)

```bash
# SQLite DB → ChromaDB 변환
python .claude/skills/md2db/scripts/md2db.py output.db --to-chroma chroma_dir/

# 청크 크기 조정
python .claude/skills/md2db/scripts/md2db.py output.db --to-chroma chroma_dir/ --chunk-size 500

# 컬렉션 이름 지정
python .claude/skills/md2db/scripts/md2db.py output.db --to-chroma chroma_dir/ --collection my_docs
```

### Step 5: 스키마 마이그레이션 (v2 신규)

```bash
# v1 DB를 v2로 마이그레이션 (백업 자동 생성)
python .claude/skills/md2db/scripts/md2db.py old.db --migrate
```

## Scripts Reference

### `scripts/md2db.py`

**Purpose:** 마크다운 ↔ SQLite DB 변환 및 관리

**Usage:**
```bash
# 변환 모드
python md2db.py <input.md> <output.db> [options]

# 조회 모드
python md2db.py <db_path> --info|--sections|--search <query>

# 내보내기 모드
python md2db.py <db_path> --export <output.md> [--section <path>] [--max-level <n>]

# ChromaDB 변환 (v2)
python md2db.py <db_path> --to-chroma <dir> [--chunk-size <n>] [--collection <name>]

# 마이그레이션 (v2)
python md2db.py <db_path> --migrate
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--append` | 기존 DB에 문서 추가 |
| `--skip-duplicates` | 동일 해시 파일 스킵 (기본값) |
| `--force-update` | 동일 해시 파일도 강제 업데이트 |
| `--info` | DB 정보 출력 |
| `--sections` | 섹션 목록 출력 |
| `--search QUERY` | 전문 검색 |
| `--export FILE` | 마크다운으로 내보내기 |
| `--section PATH` | 특정 섹션 경로 (내보내기용) |
| `--max-level N` | 내보내기 시 최대 헤더 레벨 |
| `--to-chroma DIR` | ChromaDB로 변환 (v2) |
| `--chunk-size N` | ChromaDB 청크 크기 (기본: 1000) |
| `--collection NAME` | ChromaDB 컬렉션 이름 |
| `--embed-model MODEL` | 임베딩 모델 (기본: ko-sroberta) |
| `--migrate` | v1 → v2 스키마 마이그레이션 |
| `--verbose` | 상세 로그 출력 |

## Examples

### Example 1: 대용량 문서 변환

```bash
# IBK 60년사 파일을 DB로 변환
python .claude/skills/md2db/scripts/md2db.py \
    "3_Resources/R-about_ibk/sources/IBK 60년사_시대사.md" \
    "3_Resources/R-about_ibk/outputs/ibk_history.db"
```

### Example 2: 섹션별 처리

```bash
# 섹션 목록 확인
python .claude/skills/md2db/scripts/md2db.py ibk_history.db --sections

# 특정 챕터만 추출
python .claude/skills/md2db/scripts/md2db.py ibk_history.db \
    --export chapter1.md --section "1.1"
```

### Example 3: ChromaDB 변환 (v2)

```bash
# SQLite → ChromaDB 변환
python .claude/skills/md2db/scripts/md2db.py ibk_history.db --to-chroma ibk_chroma/

# Python에서 의미 검색
from db.chroma_writer import ChromaDBWriter
writer = ChromaDBWriter('ibk_chroma/')
writer.connect()
results = writer.search("디지털 전환", top_k=5)
```

### Example 4: 여러 문서 통합

```bash
# 첫 번째 문서 변환
python .claude/skills/md2db/scripts/md2db.py doc1.md combined.db

# 추가 문서 병합 (중복 자동 감지)
python .claude/skills/md2db/scripts/md2db.py doc2.md combined.db --append
python .claude/skills/md2db/scripts/md2db.py doc3.md combined.db --append

# 통합 DB 정보 확인
python .claude/skills/md2db/scripts/md2db.py combined.db --info
```

### Example 5: 기존 DB 마이그레이션 (v2)

```bash
# v1 DB를 v2로 업그레이드
python .claude/skills/md2db/scripts/md2db.py old_v1.db --migrate

# 백업 파일 자동 생성: old_v1.v1_backup_20260114_123456.db
```

## Dependencies

### 필수 의존성

```bash
pip install PyYAML
```

### 선택적 의존성

```bash
# 진행률 표시
pip install tqdm

# ChromaDB 기능 (--to-chroma)
pip install chromadb sentence-transformers
```

## Module Structure (v2)

```
scripts/
├── md2db.py              # CLI 진입점
├── core/
│   ├── models.py         # 데이터 모델 (Block, Section, Document)
│   ├── parser.py         # MarkdownParser, YamlParser
│   └── utils.py          # FileHasher, EncodingDetector
├── db/
│   ├── schema.py         # v2 스키마 정의
│   ├── sqlite_writer.py  # SQLite 저장 (중복 감지 포함)
│   ├── sqlite_reader.py  # SQLite 조회
│   ├── chroma_writer.py  # ChromaDB 변환
│   └── migrator.py       # v1→v2 마이그레이션
└── export/
    └── markdown.py       # 마크다운 복원
```

## Best Practices

1. **대용량 파일**: 100KB 이상 파일은 DB 변환 권장
2. **중복 관리**: `--force-update` 없이 실행하면 동일 파일 자동 스킵
3. **마이그레이션**: v1 DB는 `--migrate`로 업그레이드 (백업 자동 생성)
4. **ChromaDB**: 의미 검색이 필요한 경우에만 `--to-chroma` 사용
5. **인코딩**: UTF-8 인코딩 확인 (스크립트가 자동 감지)
6. **경로**: 출력 DB는 `outputs/` 폴더에 저장 권장

## Error Handling

| 오류 | 원인 | 해결 |
|------|------|------|
| 인코딩 오류 | 비 UTF-8 파일 | 스크립트가 자동 감지하여 처리 |
| 파싱 오류 | 비정상적 마크다운 구조 | 원본 파일 수정 후 재시도 |
| DB 잠금 | 다른 프로세스 사용 중 | 다른 DB 연결 종료 후 재시도 |
| ChromaDB 오류 | 패키지 미설치 | `pip install chromadb sentence-transformers` |

## Path Convention

경로 표시 시 `>>` 사용:
- 입력: `3_Resources >> R-about_ibk >> sources >> document.md`
- 출력: `3_Resources >> R-about_ibk >> outputs >> document.db`

## See Also

- `references/schema.md`: 상세 DB 스키마 문서
- `md-cleaner` 스킬: 마크다운 클리닝
