# -*- coding: utf-8 -*-
---
name: api-fred
description: 미국 연방준비제도(Federal Reserve) FRED OpenAPI를 통해 미국 경제통계 데이터를 조회하는 스킬. 국채 금리, 연방기금금리, 실업률, 물가지수, GDP, 환율 등 미국 경제지표 수집에 활용.
version: 1.0.0
---

# FRED OpenAPI Skill

## Purpose

미국 연방준비제도(Federal Reserve) FRED OpenAPI를 통해 미국 경제통계 데이터를 조회합니다.

**핵심 기능:**
1. 시리즈 검색: 시리즈 목록 및 정보 조회
2. 시계열 데이터 조회: 기간별 경제지표 조회
3. 메타데이터 DB: 시리즈 정보 SQLite 관리
4. 데이터 저장: fred.db에 수집 데이터 저장

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 미국 국채 금리 (Treasury Rate)를 조회할 때
- 연방기금금리 (Federal Funds Rate)가 필요할 때
- 미국 실업률, CPI, PCE 등 경제지표가 필요할 때
- 원/달러 환율, GDP 성장률을 분석할 때

트리거 예시:
- "미국 10년물 국채 금리 조회해줘"
- "FRED에서 연방기금금리 데이터 가져와줘"
- "미국 CPI 추이 보여줘"
- "원달러 환율 최근 1년치 조회해줘"

## API 개요

### Base URL
```
https://api.stlouisfed.org/fred
```

### 인증
- API Key 방식 (Query Parameter: `api_key`)
- 인증키는 [FRED API Keys](https://fred.stlouisfed.org/docs/api/api_key.html)에서 신청
- 환경변수: `FRED_API_KEY`

### 주요 API 엔드포인트

| 엔드포인트 | 설명 | 용도 |
|------------|------|------|
| `series/search` | 시리즈 검색 | 시리즈 찾기 |
| `series` | 시리즈 정보 | 메타데이터 조회 |
| `series/observations` | 시계열 데이터 | 데이터 수집 |

### 빈도 코드

| 코드 | 설명 |
|------|------|
| d | Daily (일간) |
| w | Weekly (주간) |
| bw | Biweekly (격주) |
| m | Monthly (월간) |
| q | Quarterly (분기) |
| sa | Semiannual (반기) |
| a | Annual (연간) |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
FRED_API_KEY=your_api_key_here
```

API 키 발급: https://fred.stlouisfed.org/docs/api/api_key.html

## Workflow

### Step 1: 메타데이터 DB 동기화
```bash
# 전체 동기화 (기본 키워드 + 인기 시리즈)
python .claude/skills/api-fred/scripts/fred_api.py --sync

# 강제 재동기화
python .claude/skills/api-fred/scripts/fred_api.py --sync --force

# 메타DB 통계 확인
python .claude/skills/api-fred/scripts/fred_api.py --stats
```

### Step 2: 시리즈 검색
```bash
# API로 시리즈 검색
python .claude/skills/api-fred/scripts/fred_api.py --search "treasury"

# 로컬 메타DB에서 검색
python .claude/skills/api-fred/scripts/fred_api.py --search-local "interest"

# 인기 시리즈 목록
python .claude/skills/api-fred/scripts/fred_api.py --popular
```

### Step 3: 시리즈 정보 조회
```bash
# 시리즈 상세 정보
python .claude/skills/api-fred/scripts/fred_api.py --info DGS10
```

### Step 4: 데이터 조회
```bash
# 전체 기간
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10

# 기간 지정
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --start 2024-01-01 --end 2024-12-31

# 최근 N일
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --recent 365
```

### Step 5: 결과 저장
```bash
# CSV 파일로 저장
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --recent 365 --output result.csv

# JSON 파일로 저장
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --output result.json

# fred.db에 저장
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --save-db

# 저장된 데이터 조회
python .claude/skills/api-fred/scripts/fred_api.py --query-db --series DGS10
```

## Scripts Reference

### `scripts/fred_api.py`

**Purpose:** FRED OpenAPI 호출 및 데이터 처리

**Usage:**
```bash
# 메타데이터 동기화
python fred_api.py --sync [--force]

# 메타DB 통계
python fred_api.py --stats

# 시리즈 검색 (API)
python fred_api.py --search <검색어>

# 로컬 검색 (메타DB)
python fred_api.py --search-local <키워드>

# 인기 시리즈
python fred_api.py --popular

# 시리즈 정보
python fred_api.py --info <시리즈ID>

# 데이터 조회
python fred_api.py --data <시리즈ID> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
python fred_api.py --data <시리즈ID> --recent <일수>

# 데이터 저장
python fred_api.py --data <시리즈ID> --output <파일>
python fred_api.py --data <시리즈ID> --save-db

# 데이터 DB
python fred_api.py --db-stats
python fred_api.py --query-db --series <시리즈ID>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--sync` | 메타데이터 DB 동기화 |
| `--force` | 강제 동기화 |
| `--stats` | 메타DB 통계 출력 |
| `--search TEXT` | 시리즈 검색 (API) |
| `--search-local KEYWORD` | 메타DB에서 검색 |
| `--popular` | 인기 시리즈 목록 |
| `--info SERIES_ID` | 시리즈 정보 조회 |
| `--data SERIES_ID` | 시계열 데이터 조회 |
| `--start YYYY-MM-DD` | 시작일 |
| `--end YYYY-MM-DD` | 종료일 |
| `--recent DAYS` | 최근 N일 |
| `--frequency d/w/m/q/a` | 빈도 변환 |
| `--limit N` | 조회/출력 건수 |
| `--output FILE` | 결과 저장 (json/csv) |
| `--save-db` | fred.db에 저장 |
| `--db-stats` | 데이터 DB 통계 |
| `--query-db` | 데이터 DB 조회 |
| `--series SERIES_ID` | DB 조회 시 시리즈 지정 |

### `scripts/fred_meta_db.py`

**Purpose:** 메타데이터 SQLite DB 관리

**Usage:**
```bash
# DB 초기화
python fred_meta_db.py --init

# 키워드 기반 동기화
python fred_meta_db.py --sync-search "treasury"

# 인기 시리즈 동기화
python fred_meta_db.py --sync-popular

# 전체 동기화
python fred_meta_db.py --sync-all [--force]

# 시리즈 검색
python fred_meta_db.py --search "interest"

# FTS 전문검색
python fred_meta_db.py --search-fts "treasury rate"

# 시리즈 정보
python fred_meta_db.py --info DGS10

# 인기 시리즈 목록
python fred_meta_db.py --popular [--category 금리]

# DB 통계
python fred_meta_db.py --stats
```

## 주요 시리즈 코드

### 금리

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| DGS1 | 1년 국채 금리 | D |
| DGS2 | 2년 국채 금리 | D |
| DGS3 | 3년 국채 금리 | D |
| DGS5 | 5년 국채 금리 | D |
| DGS7 | 7년 국채 금리 | D |
| DGS10 | 10년 국채 금리 | D |
| DGS20 | 20년 국채 금리 | D |
| DGS30 | 30년 국채 금리 | D |
| FEDFUNDS | 연방기금금리 | M |
| DFEDTARU | 연방기금 목표금리 상한 | D |
| DFEDTARL | 연방기금 목표금리 하한 | D |
| T10Y2Y | 10년-2년 금리 스프레드 | D |
| T10Y3M | 10년-3개월 금리 스프레드 | D |

### 고용

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| UNRATE | 실업률 | M |
| PAYEMS | 비농업 고용자 수 | M |
| ICSA | 실업수당 청구건수 | W |

### 물가

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| CPIAUCSL | 소비자물가지수(CPI) | M |
| CPILFESL | 근원 CPI | M |
| PCEPI | PCE 물가지수 | M |
| PCEPILFE | 근원 PCE | M |

### GDP

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| GDP | 명목 GDP | Q |
| GDPC1 | 실질 GDP | Q |
| A191RL1Q225SBEA | 실질 GDP 성장률 | Q |

### 환율

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| DEXKOUS | 원/달러 환율 | D |
| DEXJPUS | 엔/달러 환율 | D |
| DEXUSEU | 유로/달러 환율 | D |
| DEXCHUS | 위안/달러 환율 | D |

### 기타

| 코드 | 시리즈명 | 빈도 |
|------|----------|------|
| SP500 | S&P 500 지수 | D |
| NASDAQCOM | 나스닥 종합지수 | D |
| VIXCLS | VIX 변동성 지수 | D |
| M2SL | M2 통화량 | M |
| WALCL | 연준 총자산 | W |

## Examples

### Example 1: 10년 국채 금리 조회
```bash
# 최근 1년 데이터
python .claude/skills/api-fred/scripts/fred_api.py --data DGS10 --recent 365
```

**출력:**
```
=== [DGS10] 10-Year Treasury Constant Maturity Rate (252건) ===
기간: 2024-01-22 ~ 2025-01-22
날짜         값                   단위
--------------------------------------------------
2025-01-22   4.65                 Percent
2025-01-21   4.59                 Percent
...
```

### Example 2: 시리즈 정보 조회
```bash
python .claude/skills/api-fred/scripts/fred_api.py --info FEDFUNDS
```

**출력:**
```
=== 시리즈 정보: FEDFUNDS ===
시리즈 ID: FEDFUNDS
제목: Federal Funds Effective Rate
빈도: Monthly (M)
단위: Percent
계절조정: Not Seasonally Adjusted
기간: 1954-07-01 ~ 2024-12-01
인기도: 93
한글명: 연방기금금리
```

### Example 3: Python 직접 사용
```python
from scripts.fred_api import FredAPI

api = FredAPI()

# 시리즈 검색
result = api.search_series("treasury rate", limit=10)
for s in result.get('seriess', []):
    print(f"{s['id']}: {s['title']}")

# 시계열 데이터 조회
data = api.get_observations(
    series_id="DGS10",
    observation_start="2024-01-01",
    observation_end="2024-12-31"
)

for obs in data.get('observations', []):
    if obs['value'] != '.':
        print(f"{obs['date']}: {obs['value']}%")

# DB 저장
api.save_to_db(data, "DGS10")
```

## Korean Encoding (한글 인코딩)

**중요:** 모든 파일 작업에 UTF-8 인코딩 사용

```python
# 파일 읽기/쓰기
with open(file, 'r', encoding='utf-8') as f:
    data = f.read()

# CSV 저장 (Excel 호환)
with open(file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
```

## Error Handling

| 상황 | 원인 | 해결 |
|------|------|------|
| `API 키가 설정되지 않았습니다` | FRED_API_KEY 없음 | .claude/.env에 키 설정 |
| `HTTP 400` | 잘못된 요청 | 파라미터 확인 |
| `HTTP 429` | 요청 제한 초과 | 호출 간격 조정 |
| `값이 '.'` | 결측치 | 해당 날짜 데이터 없음 |

## Data Directory

### 데이터 파일 위치
```
.claude/skills/api-fred/
├── data/
│   └── fred_meta.db         # 메타데이터 SQLite DB
└── scripts/
    ├── fred_api.py          # 메인 API 클라이언트
    └── fred_meta_db.py      # 메타DB 관리

3_Resources/R-DB/
└── fred.db                  # 시계열 데이터 저장
```

### 메타데이터 DB 스키마
```sql
-- 시리즈 목록
CREATE TABLE series (
    id INTEGER PRIMARY KEY,
    series_id TEXT UNIQUE NOT NULL,
    title TEXT,
    frequency TEXT,
    frequency_short TEXT,
    units TEXT,
    seasonal_adjustment TEXT,
    observation_start TEXT,
    observation_end TEXT,
    popularity INTEGER,
    notes TEXT,
    last_updated TEXT,
    updated_at TEXT
);

-- 인기 시리즈 (빠른 접근용)
CREATE TABLE popular_series (
    id INTEGER PRIMARY KEY,
    series_id TEXT UNIQUE NOT NULL,
    title TEXT,
    category TEXT,
    description_kr TEXT,
    updated_at TEXT
);

-- FTS5 전문검색
CREATE VIRTUAL TABLE series_fts USING fts5(
    title, notes, units,
    content='series', content_rowid='id'
);
```

### 데이터 DB 스키마
```sql
-- 시계열 데이터
CREATE TABLE fred_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,
    title TEXT,
    date TEXT NOT NULL,       -- YYYY-MM-DD
    value TEXT,               -- '.'은 결측치
    frequency TEXT,
    units TEXT,
    raw_data TEXT,
    collected_at TEXT,
    UNIQUE(series_id, date)
);

-- 수집 로그
CREATE TABLE collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT,
    observation_start TEXT,
    observation_end TEXT,
    status TEXT,
    record_count INTEGER,
    error_message TEXT,
    collected_at TEXT
);
```

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-fred >> scripts >> fred_api.py`
- 메타DB: `.claude >> skills >> api-fred >> data >> fred_meta.db`
- 데이터DB: `3_Resources >> R-DB >> fred.db`

## Limitations

- API 호출 제한: 120 requests/minute
- 결측치: value가 `.`인 경우 해당 날짜 데이터 없음
- 날짜 형식: YYYY-MM-DD (한국 API와 다름)
- 시리즈 ID: 영문 약어 (DGS10, UNRATE 등)

## See Also

- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [FRED API Keys](https://fred.stlouisfed.org/docs/api/api_key.html)
- `api-ecos` 스킬: 한국은행 경제통계
- `api-kosis` 스킬: 국가통계포털
- `md2db` 스킬: 분석 결과 DB 저장
