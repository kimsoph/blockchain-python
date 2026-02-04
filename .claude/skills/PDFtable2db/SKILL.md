---
name: PDFtable2db
description: PDF 파일에서 표(table)를 추출하여 SQLite DB로 임포트하는 스킬. pdfplumber를 사용하여 격자형 표를 정확하게 추출하고, 정규화된 스키마로 저장. 금융 보고서, 재무제표 등 다중 표 PDF 처리에 최적화.
version: 1.0.0
---

# PDF Table to Database Skill

## Purpose

PDF 파일에 포함된 표(table) 데이터를 추출하여 SQLite 데이터베이스로 저장합니다. 금융 보고서, 재무제표, 통계 자료 등 다수의 표가 포함된 PDF 문서를 구조화된 데이터로 변환합니다.

**핵심 기능:**
1. PDF에서 모든 표 자동 추출 (pdfplumber 기반)
2. 표 메타데이터 관리 (페이지, 위치, 회사명 등)
3. 정규화된 DB 스키마로 저장
4. 한글 데이터 완벽 지원 (UTF-8)
5. CSV/마크다운 내보내기

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- PDF에서 표 데이터를 추출해야 할 때
- 금융 보고서의 재무 데이터를 DB로 저장할 때
- 여러 표를 통합 분석해야 할 때
- 표 데이터를 SQL로 쿼리하고 싶을 때

트리거 예시:
- "이 PDF의 표를 DB로 변환해줘"
- "PDF에서 재무제표 추출해서 저장해줘"
- "표 데이터를 SQLite로 임포트해줘"

## Architecture

### DB 스키마 구조

```
pdf_sources (PDF 메타데이터)
    └── tables (표 정보)
            └── table_data (셀 데이터)
```

### 테이블 설명

| 테이블 | 설명 | 주요 필드 |
|--------|------|-----------|
| `pdf_sources` | PDF 파일 정보 | filename, title, total_pages |
| `tables` | 추출된 표 정보 | page_num, table_index, rows, cols, category |
| `table_data` | 표의 셀 데이터 | row_idx, col_idx, value, header |
| `table_headers` | 표 헤더 정보 | col_idx, header_name |

### 금융 보고서용 확장 스키마 (선택)

```sql
-- 회사 마스터 (금융 보고서용)
companies (id, name, name_eng)

-- 지표 마스터
metrics (id, category, name_kor, name_eng, unit)

-- 시계열 데이터
financial_data (company_id, metric_id, year, is_estimate, value)
```

### 단위 자동 할당 규칙

`--financial` 모드에서 지표 저장 시 자동으로 단위가 할당됩니다:

| 단위 | 적용 지표 | 예시 |
|------|----------|------|
| **십억원** | 재무상태표/손익계산서 금액 항목 | 자산총계, 당기순이익, 영업이익, 이자수익 |
| **원** | 주당 금액 | EPS, 주당장부가, 주당배당금 |
| **%** | 비율 지표 | ROAA, ROAE, NIM, BIS비율, 배당성향 |

**패턴 기반 매칭:**
- `비율`, `성장률`, `ratio`, `margin` 포함 → `%`
- `주당`, `EPS` 포함 → `원`

**단위 조회 예시:**
```sql
SELECT c.name, m.name_kor, m.unit, f.year, f.value
FROM financial_data f
JOIN companies c ON f.company_id = c.id
JOIN metrics m ON f.metric_id = m.id
WHERE c.name = '신한지주' AND m.name_kor = '당기순이익';

-- 결과: 신한지주 | 당기순이익 | 십억원 | 2024 | 4558
```

## Installation

### 필수 의존성

```bash
pip install pdfplumber pandas
```

### 선택 의존성 (더 나은 표 추출)

```bash
pip install camelot-py[cv]  # Ghostscript 필요
pip install tabula-py       # Java 필요
```

## Workflow

### Step 1: PDF에서 표 추출 및 DB 저장

```bash
# 기본 사용법
python .claude/skills/PDFtable2db/scripts/pdftable2db.py input.pdf output.db

# 특정 페이지만 처리
python .claude/skills/PDFtable2db/scripts/pdftable2db.py input.pdf output.db --pages 1-5

# 금융 보고서 모드 (회사/지표 정규화)
python .claude/skills/PDFtable2db/scripts/pdftable2db.py input.pdf output.db --financial
```

### Step 2: DB 조회

```bash
# DB 정보 확인
python .claude/skills/PDFtable2db/scripts/pdftable2db.py output.db --info

# 표 목록 조회
python .claude/skills/PDFtable2db/scripts/pdftable2db.py output.db --list-tables

# 특정 표 조회
python .claude/skills/PDFtable2db/scripts/pdftable2db.py output.db --show-table 1
```

### Step 3: 데이터 내보내기

```bash
# CSV로 내보내기
python .claude/skills/PDFtable2db/scripts/pdftable2db.py output.db --export-csv output_dir/

# 마크다운으로 내보내기
python .claude/skills/PDFtable2db/scripts/pdftable2db.py output.db --export-md output.md
```

## Scripts Reference

### `scripts/pdftable2db.py`

**Purpose:** PDF 표 추출 및 SQLite DB 관리

**Usage:**
```bash
# 추출 모드
python pdftable2db.py <input.pdf> <output.db> [options]

# 조회 모드
python pdftable2db.py <db_path> --info|--list-tables|--show-table <id>

# 내보내기 모드
python pdftable2db.py <db_path> --export-csv <dir>|--export-md <file>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--pages RANGE` | 처리할 페이지 범위 (예: "1-5", "1,3,5") |
| `--financial` | 금융 보고서 모드 (정규화 스키마) |
| `--min-rows N` | 최소 행 수 (기본: 2) |
| `--encoding ENC` | 출력 인코딩 (기본: utf-8) |
| `--info` | DB 정보 출력 |
| `--list-tables` | 표 목록 출력 |
| `--show-table ID` | 특정 표 내용 출력 |
| `--export-csv DIR` | CSV로 내보내기 |
| `--export-md FILE` | 마크다운으로 내보내기 |

## Examples

### Example 1: 삼성증권 은행 리포트 처리

```bash
# PDF에서 표 추출
python .claude/skills/PDFtable2db/scripts/pdftable2db.py \
    "9_Attachments/Documents/samsung_bank_20251125_p71-79.pdf" \
    "3_Resources/R-DB/samsung_bank_tables.db" \
    --financial

# 추출 결과 확인
python .claude/skills/PDFtable2db/scripts/pdftable2db.py \
    "3_Resources/R-DB/samsung_bank_tables.db" --info
```

### Example 2: 특정 페이지만 처리

```bash
# 71-73 페이지만 처리
python .claude/skills/PDFtable2db/scripts/pdftable2db.py \
    report.pdf output.db --pages 71-73
```

### Example 3: 데이터 분석

```bash
# SQLite로 직접 쿼리
sqlite3 output.db "SELECT * FROM tables"

# 특정 회사 데이터 조회 (금융 모드)
sqlite3 output.db "
    SELECT c.name, m.name_kor, f.year, f.value
    FROM financial_data f
    JOIN companies c ON f.company_id = c.id
    JOIN metrics m ON f.metric_id = m.id
    WHERE c.name = 'KB금융'
"
```

## Korean Encoding (한글 인코딩)

**중요:** 이 스킬은 한글 데이터 처리에 최적화되어 있습니다.

1. **파일 읽기/쓰기**: 모든 파일 작업에 `encoding='utf-8'` 명시
2. **SQLite**: `PRAGMA encoding = 'UTF-8'` 설정
3. **CSV 내보내기**: UTF-8 BOM 포함 옵션 제공
4. **콘솔 출력**: `sys.stdout` 인코딩 확인

```python
# 스크립트 내부 처리 방식
with open(file, 'r', encoding='utf-8') as f:
    ...

conn.execute("PRAGMA encoding = 'UTF-8'")
```

## Error Handling

| 오류 | 원인 | 해결 |
|------|------|------|
| 표 추출 실패 | 이미지 기반 PDF | OCR 도구 사용 권장 |
| 인코딩 오류 | 비 UTF-8 소스 | `--encoding` 옵션 지정 |
| 빈 표 | 최소 행 수 미달 | `--min-rows` 조정 |
| 병합 셀 오류 | 복잡한 표 구조 | 수동 후처리 필요 |

## Path Convention

경로 표시 시 `>>` 사용:
- 입력: `9_Attachments >> Documents >> report.pdf`
- 출력: `3_Resources >> R-DB >> report_tables.db`

## See Also

- `md2db` 스킬: 마크다운 → DB 변환
- `md-cleaner` 스킬: 마크다운 클리닝
- pdfplumber 문서: https://github.com/jsvine/pdfplumber
