# textbook-db-analyzer

*버전: 1.0*
*최종 업데이트: 2026-01-07*

## 개요

ibk_textbook.db를 활용하여 IBK 경영지표의 다기간 비교 분석을 수행하는 스킬.

## 용도

- textBook 마크다운 데이터가 저장된 SQLite DB에서 지표 추출
- 여러 기간(월/분기/년)의 동일 지표 비교 분석
- 다기간 추이 차트 데이터 자동 생성
- textbook-analyzer 에이전트와 연동하여 정확한 히스토리 데이터 제공

## 사전 조건

- `ibk_textbook.db` 파일 존재 (위치: `3_Resources/R-DB/`)
- md2db 스킬로 textBook 마크다운 파일들이 DB로 변환되어 있어야 함

## DB 스키마

```sql
-- documents: 문서 메타데이터
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    title TEXT,
    frontmatter TEXT,
    created_at TIMESTAMP
);

-- sections: 헤더 기반 계층 구조
CREATE TABLE sections (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    level INTEGER,
    title TEXT,
    path TEXT,
    parent_id INTEGER,
    position INTEGER
);

-- blocks: 콘텐츠 블록
CREATE TABLE blocks (
    id INTEGER PRIMARY KEY,
    section_id INTEGER,
    type TEXT,
    content TEXT,
    raw_markdown TEXT,
    position INTEGER
);

-- blocks_fts: 전문 검색 (FTS5)
CREATE VIRTUAL TABLE blocks_fts USING fts5(content);
```

## 핵심 기능

### 1. get_metric_trend(metric_name, periods)
특정 지표의 다기간 추이 조회

```python
# 예시: ROA 지표의 3년 추이
result = analyzer.get_metric_trend('ROA', ['202403', '202406', '202409', '202412', '202503', '202506', '202509', '202510'])
# 반환: {'labels': ['2024.03', '2024.06', ...], 'values': [0.70, 0.68, ...]}
```

### 2. compare_periods(metric_name, period1, period2)
두 시점 간 지표 비교

```python
# 예시: 전년 동월 대비 당기순이익 비교
result = analyzer.compare_periods('당기순이익', '202410', '202510')
# 반환: {'prev': 24281, 'current': 21050, 'change': -3231, 'change_pct': -13.3}
```

### 3. generate_comparison_chart(metrics, periods)
다기간 비교 차트 데이터 생성

```python
# 예시: 5대 핵심 지표의 분기별 비교 데이터
result = analyzer.generate_comparison_chart(
    metrics=['ROA', 'ROE', '연체율', 'BIS비율', '총자산'],
    periods=['202403', '202406', '202409', '202412', '202503', '202506', '202509', '202510']
)
# 반환: make-chart 스킬에 바로 전달 가능한 dict 형식
```

### 4. extract_chapter_metrics(period, chapter_num)
특정 기간/챕터의 모든 지표 추출

```python
# 예시: 2025년 10월 VI. 건전성현황의 모든 지표
result = analyzer.extract_chapter_metrics('202510', 6)
# 반환: [{'name': '고정이하여신비율', 'value': 1.46, 'unit': '%'}, ...]
```

## 사용 방법

### 기본 사용

```python
from textbook_db_analyzer import TextbookDBAnalyzer

# DB 연결
analyzer = TextbookDBAnalyzer('3_Resources/R-DB/ibk_textbook.db')

# 다기간 추이 조회
trend = analyzer.get_metric_trend('당기순이익', ['202403', '202406', '202409', '202412'])

# 전년 동월 비교
comparison = analyzer.compare_periods('ROA', '202410', '202510')

# DB 연결 종료
analyzer.close()
```

### textbook-analyzer 에이전트와 연동

```python
# Phase 2: 챕터 분석 시 DB에서 히스토리 데이터 조회
historical_data = analyzer.get_metric_trend('ROA', periods)

# Phase 4: Executive Summary 생성 시 정확한 수치 추출
metrics = analyzer.extract_chapter_metrics(current_period, chapter_num=1)

# Phase 5: 비교 인포그래픽용 데이터 생성
comparison_data = analyzer.generate_comparison_chart(
    metrics=['당기순이익', 'ROA', '연체율', 'BIS비율', '총자산'],
    periods=[prev_year_period, current_period]
)
```

## 지표 매핑

### 주요 지표명 (정규식 패턴)

| 구분 | 지표명 패턴 | 예시 |
|------|-----------|------|
| 수익성 | `당기순이익`, `ROA`, `ROE`, `NIM` | "당기순이익: 21,050억원" |
| 건전성 | `고정이하여신비율`, `연체율`, `Coverage Ratio` | "연체율(표면): 1.21%" |
| 자본적정성 | `BIS비율`, `CET1비율` | "BIS비율: 14.89%" |
| 성장성 | `총자산`, `중소기업대출`, `총수신` | "총자산: 447.5조원" |

### 숫자 파싱 규칙

```python
# 조원 단위: "447.5조원" -> 447.5 (조원)
# 억원 단위: "21,050억원" -> 21050 (억원)
# 퍼센트: "1.46%" -> 1.46 (%)
# bp 단위: "+15bp" -> 0.15 (%p)
```

## 출력 위치

스킬 자체는 데이터만 반환하며, 차트/인포그래픽 생성은 make-chart, make-infographic 스킬에 위임.

## 에러 처리

| 상황 | 처리 방법 |
|------|---------|
| DB 파일 없음 | FileNotFoundError + 예상 경로 안내 |
| 지표 미발견 | None 반환 + 경고 로그 |
| 기간 데이터 없음 | 빈 리스트 반환 |
| 파싱 실패 | 원본 텍스트 유지 + 경고 |

## 관련 스킬

- **md2db**: 마크다운 → SQLite DB 변환 (선행 작업)
- **make-chart**: 추이 차트 생성 (후행 작업)
- **make-infographic**: 비교 인포그래픽 생성 (후행 작업)

## 파일 구조

```
.claude/skills/textbook-db-analyzer/
├── SKILL.md              # 이 파일
└── scripts/
    ├── db_analyzer.py    # 핵심 분석 로직
    └── metric_parser.py  # 지표 추출 및 파싱
```
