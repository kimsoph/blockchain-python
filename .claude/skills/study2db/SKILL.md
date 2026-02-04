---
name: study2db
description: 학습 자료를 SQLite DB로 변환하여 AI가 효율적으로 조회/활용할 수 있도록 함. 분석보고서 작성 시 context size 문제 해결.
version: 1.1.0
---

# study2db

## Changelog

### v1.1.0 (2026-01-14)
- **스키마 버전 관리 도입**: `schema_version` 테이블 추가
- **YAML 파싱 고도화**: PyYAML 기반 파싱 (배열, 중첩 객체 지원)
- **마이그레이션 지원**: v1 → v2 자동 마이그레이션, 백업 생성
- **새 CLI 명령**: `migrate` - 기존 DB 업그레이드

## Purpose

다양한 형식의 파일(md, txt, csv, db, pdf)을 통합 SQLite DB로 변환하여 AI가 효율적으로 조회하고 활용할 수 있도록 합니다. 분석보고서 작성 시 많은 자료를 공부해야 할 때 발생하는 **context size 문제를 해결**합니다.

### 핵심 기능

1. **다중 파일 형식 지원**: md, txt, csv, db, pdf
2. **파일 구조 보존**: 원본 파일의 계층 구조와 관계 유지
3. **핵심 내용 추출**: LLM 기반 요약, 핵심 포인트, 사실, 정의, 권고 추출
4. **전문 검색**: FTS5 기반 빠른 검색
5. **구조화 데이터**: CSV/테이블 데이터를 JSON으로 저장

---

## When to Use This Skill

다음 상황에서 이 스킬을 사용하세요:

- 분석보고서 작성 전 여러 자료를 미리 학습해야 할 때
- 대용량 문서들의 핵심 내용만 추출하고 싶을 때
- 여러 파일의 정보를 통합하여 검색하고 싶을 때
- context size 제한으로 모든 자료를 한번에 읽을 수 없을 때

### 예시 트리거

```
"IBK 전략 보고서 작성을 위해 이 자료들을 먼저 학습해줘"
"이 PDF들을 DB로 변환해서 필요할 때 조회할 수 있게 해줘"
"여러 문서에서 핵심 내용만 추출해서 저장해줘"
```

---

## Architecture

### 폴더 구조

```
.claude/skills/study2db/
├── SKILL.md                 # 이 문서
├── scripts/
│   └── study2db.py          # 메인 스크립트
└── references/
    └── schema.sql           # DB 스키마 정의
```

### DB 스키마 (ERD)

```
study_projects (프로젝트)
    │
    └── source_files (원본 파일)
            │
            ├── content_chunks (콘텐츠 청크)
            │       │
            │       └── key_insights (핵심 인사이트)
            │
            ├── structured_data (CSV/테이블 데이터)
            │
            └── external_db_tables (외부 DB 테이블 정보)

[FTS5 전문검색]
content_fts ← content_chunks
insights_fts ← key_insights
```

### 핵심 테이블

| 테이블 | 설명 |
|--------|------|
| `study_projects` | 스터디/프로젝트 메타데이터 |
| `source_files` | 원본 파일 정보 (경로, 해시, 상태) |
| `content_chunks` | 파싱된 콘텐츠 청크 |
| `key_insights` | LLM 추출 핵심 내용 |
| `structured_data` | CSV/테이블 구조화 데이터 |
| `external_db_tables` | 외부 DB 테이블 참조 |

### insight_type 정의

| 타입 | 설명 | 중요도 |
|------|------|--------|
| `summary` | 섹션/파일 전체 요약 | 4-5 |
| `key_point` | 핵심 포인트, 주요 논점 | 4-5 |
| `fact` | 수치, 날짜, 통계 정보 | 3-4 |
| `definition` | 개념/용어 정의 | 3 |
| `recommendation` | 행동 제안/권고 | 3-4 |

---

## Workflow

### Step 1: 파일 임포트

```bash
python .claude/skills/study2db/scripts/study2db.py import \
    "3_Resources/R-DB/study_ibk_strategy.db" \
    "자료1.md" "자료2.pdf" "데이터.csv" \
    --name "IBK 전략분석" \
    --purpose "2026 경영전략 보고서 작성"
```

### Step 2: LLM 핵심 추출

```bash
python .claude/skills/study2db/scripts/study2db.py extract \
    "3_Resources/R-DB/study_ibk_strategy.db"
```

### Step 3: 정보 조회

```bash
# DB 정보
python study2db.py info study.db

# 파일 목록
python study2db.py files study.db

# 요약 조회
python study2db.py summary study.db
```

### Step 4: 검색

```bash
# 기본 검색
python study2db.py search study.db "디지털 전환"

# 타입 필터
python study2db.py search study.db "전략" --type key_point

# 중요도 필터
python study2db.py search study.db "ROE" --importance 4
```

---

## Scripts Reference

### study2db.py

메인 스크립트. 다음 명령어를 지원합니다:

| 명령 | 설명 | 예시 |
|------|------|------|
| `import` | 파일 임포트 | `study2db.py import out.db file1.md file2.pdf` |
| `extract` | LLM 핵심 추출 | `study2db.py extract out.db` |
| `info` | DB 정보 조회 | `study2db.py info out.db` |
| `files` | 파일 목록 | `study2db.py files out.db` |
| `summary` | 요약 조회 | `study2db.py summary out.db` |
| `search` | 검색 | `study2db.py search out.db "키워드"` |
| `migrate` | 스키마 업그레이드 | `study2db.py migrate out.db` |

### import 옵션

```bash
python study2db.py import <db_path> <files...> [옵션]

옵션:
  --name, -n      프로젝트명 (기본: DB 파일명)
  --purpose, -p   분석 목적
```

### search 옵션

```bash
python study2db.py search <db_path> <query> [옵션]

옵션:
  --type, -t       인사이트 타입 (summary, key_point, fact, definition, recommendation)
  --importance, -i 최소 중요도 (1-5)
```

### migrate 옵션

```bash
python study2db.py migrate <db_path> [옵션]

옵션:
  --no-backup      백업 생성 안함 (기본: 자동 백업)
```

---

## Examples

### Example 1: IBK 전략 보고서 준비

```bash
# 1. 자료 임포트
python study2db.py import \
    "3_Resources/R-DB/study_ibk_strategy.db" \
    "R-about_ibk/notes/textBook_202411_clean.md" \
    "R-about_ibk/sources/IBK_60년사.md" \
    "R-DB/fisis.db" \
    --name "IBK 2026 전략" \
    --purpose "IBK 2026년 경영전략 보고서 작성"

# 2. 핵심 추출
python study2db.py extract "3_Resources/R-DB/study_ibk_strategy.db"

# 3. 요약 확인
python study2db.py summary "3_Resources/R-DB/study_ibk_strategy.db"
```

### Example 2: 학술 자료 정리

```bash
# 논문 및 자료 통합
python study2db.py import \
    "3_Resources/R-DB/study_ai_ethics.db" \
    "papers/*.pdf" "notes/*.md" "data.csv" \
    --name "AI 윤리 연구" \
    --purpose "AI 윤리 가이드라인 작성"

# 정의 검색 (용어집 구축)
python study2db.py search "3_Resources/R-DB/study_ai_ethics.db" \
    "" --type definition
```

### Example 3: AI가 DB 조회하여 보고서 작성

```sql
-- 1. 핵심 포인트 조회 (중요도 4 이상)
SELECT content, importance, file_name
FROM key_insights ki
JOIN source_files sf ON ki.file_id = sf.id
WHERE insight_type = 'key_point' AND importance >= 4
ORDER BY importance DESC;

-- 2. 사실/데이터 근거 검색
SELECT ki.content, sf.file_name, cc.title
FROM key_insights ki
JOIN source_files sf ON ki.file_id = sf.id
LEFT JOIN content_chunks cc ON ki.chunk_id = cc.id
WHERE ki.insight_type = 'fact';

-- 3. 전문 검색
SELECT * FROM insights_fts WHERE insights_fts MATCH '디지털 전환';
```

---

## Integration with Other Skills

### md-cleaner와 연동

PDF 변환 후 마크다운 정리:

```bash
# 1. PDF → 마크다운 (markitdown CLI)
# 2. 마크다운 정리 (md-cleaner 스킬)
# 3. study2db로 DB 저장
python study2db.py import output.db "document_clean.md"
```

### md2db와의 차이점

| 항목 | md2db | study2db |
|------|-------|----------|
| 입력 | 단일 MD 파일 | 복수 파일, 다양한 형식 |
| 출력 | 구조 그대로 저장 | 핵심 내용 추출 |
| 목적 | 문서 구조화 | 학습 자료 통합 |
| LLM | 미사용 | 핵심 추출에 사용 |

---

## Best Practices

1. **파일명 규칙**: `study_주제명.db` 형식 사용
   - 예: `study_ibk_strategy.db`

2. **저장 경로**: `3_Resources/R-DB/`에 저장

3. **경로 표시**: `>>` 형식 사용
   - 예: `R-DB >> outputs >> study_ibk_strategy.db`

4. **핵심 추출 실행**: 임포트 후 반드시 `extract` 명령 실행

5. **중요도 활용**: 보고서 작성 시 `importance >= 4` 필터 권장

---

## Error Handling

### 지원하지 않는 파일 형식

```
지원하지 않는 형식: document.docx
```
→ `markitdown` CLI로 먼저 마크다운 변환 후 사용

### PDF 파싱 오류

```
PDF 파싱 실패: pdfplumber가 설치되지 않음
```
→ `pip install pdfplumber` 실행

### LLM 추출 오류

```
LLM 추출 오류: ..., 패턴 기반 추출로 대체
```
→ ANTHROPIC_API_KEY 환경변수 확인, 또는 패턴 기반 결과 사용

---

## Path Convention

- 입력 파일: 상대/절대 경로 모두 가능
- 출력 DB: `3_Resources >> R-DB >> outputs >> study_주제명.db`
- 경로 표시: `/`, `\` 대신 `>>` 사용

---

## See Also

- [[.claude/skills/md2db/SKILL|md2db]] - 마크다운 → SQLite 변환
- [[.claude/skills/PDFtable2db/SKILL|PDFtable2db]] - PDF 표 → SQLite 변환
- `markitdown` CLI - 문서 → 마크다운 변환 (`python -m markitdown`)
