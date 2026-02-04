# -*- coding: utf-8 -*-
---
name: api-apt
description: 국토교통부 아파트 매매/전월세 실거래가 API를 통해 아파트 거래 데이터를 조회하는 스킬. 지역별/기간별 아파트 매매 및 전월세 실거래가 수집 및 분석에 활용.
version: 3.0.0
---

# 아파트 실거래가 API Skill

## Purpose

국토교통부 아파트 매매/전월세 실거래가 API를 통해 전국 아파트 거래 데이터를 조회합니다.

**핵심 기능:**
1. **매매** 거래 데이터 조회: 지역별/기간별 아파트 매매 실거래가 조회
2. **전월세** 거래 데이터 조회: 지역별/기간별 아파트 전월세 실거래가 조회
3. 데이터 동기화: API 데이터를 SQLite DB에 저장
4. 거래 검색: 아파트명/법정동으로 검색
5. 고가 거래 분석: TOP N 고가 거래 조회

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 특정 지역의 아파트 매매/전월세 실거래가를 조회할 때
- 아파트 시세 추이를 분석할 때
- 고가 거래 현황을 파악할 때
- 지역별 거래량을 비교할 때
- 전세/월세 시세를 확인할 때

트리거 예시:
- "용산구 아파트 실거래가 조회해줘"
- "강남구 2024년 아파트 거래 현황 보여줘"
- "한남더힐 거래 내역 찾아줘"
- "서울 고가 아파트 거래 TOP 10"
- "이태원주공 전월세 가격 알려줘"
- "용산구 전세 시세 조회해줘"

## API 개요

### Base URL
```
https://apis.data.go.kr/1613000/
```

### 엔드포인트

| 유형 | 엔드포인트 | 설명 |
|------|-----------|------|
| 매매 | `RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade` | 아파트 매매 실거래가 |
| 매매(상세) | `RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev` | 아파트 매매 실거래 상세자료 |
| 전월세 | `RTMSDataSvcAptRent/getRTMSDataSvcAptRent` | 아파트 전월세 실거래가 |

### 인증
- Query 파라미터: `serviceKey={API_KEY}`
- 환경변수: `APT_API_KEY`

### 주요 파라미터

| 파라미터 | 필수 | 설명 | 예시 |
|----------|------|------|------|
| `serviceKey` | O | API 인증키 | - |
| `LAWD_CD` | O | 지역코드 (법정동 앞 5자리) | 11170 |
| `DEAL_YMD` | O | 계약년월 | 202511 |
| `pageNo` | O | 페이지번호 | 1 |
| `numOfRows` | O | 페이지당 건수 | 1000 |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
APT_API_KEY=your_api_key_here
```

### API 활용신청
1. [공공데이터포털](https://www.data.go.kr/) 접속 및 로그인
2. "국토교통부_아파트매매 실거래자료" 검색 (서비스ID: `15126468`)
3. 활용신청 후 승인 대기 (자동승인)

## Workflow

### Step 1: 매매 데이터 동기화
```bash
# 특정 지역/년월 동기화
python .claude/skills/api-apt/scripts/apt_api.py --sync --region 11170 --ym 202511

# 기간 범위 동기화
python .claude/skills/api-apt/scripts/apt_api.py --sync --region 11170 --ym 202501-202512

# DB 통계 확인
python .claude/skills/api-apt/scripts/apt_api.py --stats
```

### Step 2: 전월세 데이터 동기화
```bash
# 전월세 동기화 (--rent 옵션 추가)
python .claude/skills/api-apt/scripts/apt_api.py --rent --sync --region 11170 --ym 202511

# 전월세 기간 범위 동기화
python .claude/skills/api-apt/scripts/apt_api.py --rent --sync --region 11170 --ym 202501-202512

# 전월세 DB 통계
python .claude/skills/api-apt/scripts/apt_api.py --rent --stats
```

### Step 3: 데이터 검색
```bash
# 매매 검색
python .claude/skills/api-apt/scripts/apt_api.py --search "한남더힐"

# 전월세 검색
python .claude/skills/api-apt/scripts/apt_api.py --rent --search "한남더힐"

# 지역 필터 추가
python .claude/skills/api-apt/scripts/apt_api.py --search "아파트" --region 11680
```

### Step 4: 고가 거래 조회
```bash
# 매매 고가 거래 TOP 20
python .claude/skills/api-apt/scripts/apt_api.py --top 20

# 전월세 고가 거래 TOP 20
python .claude/skills/api-apt/scripts/apt_api.py --rent --top 20

# 전세만 조회
python .claude/skills/api-apt/scripts/apt_api.py --rent --top 10 --jeonse

# 월세만 조회
python .claude/skills/api-apt/scripts/apt_api.py --rent --top 10 --monthly

# 특정 지역/년월 고가 거래
python .claude/skills/api-apt/scripts/apt_api.py --top 10 --region 11170 --ym 202511
```

### Step 5: 결과 저장
```bash
# CSV 파일로 저장
python .claude/skills/api-apt/scripts/apt_api.py --search "한남" --output result.csv

# JSON 파일로 저장
python .claude/skills/api-apt/scripts/apt_api.py --top 50 --output result.json
```

## Scripts Reference

### `scripts/apt_api.py`

**Purpose:** 매매/전월세 API 호출 및 CLI

**Usage:**
```bash
# 매매 데이터 동기화
python apt_api.py --sync --region <지역코드> --ym <년월>

# 전월세 데이터 동기화
python apt_api.py --rent --sync --region <지역코드> --ym <년월>

# DB 통계
python apt_api.py --stats           # 매매
python apt_api.py --rent --stats    # 전월세

# 검색
python apt_api.py --search <키워드>          # 매매
python apt_api.py --rent --search <키워드>   # 전월세

# 고가 거래
python apt_api.py --top <N>                        # 매매
python apt_api.py --rent --top <N>                 # 전월세
python apt_api.py --rent --top <N> --jeonse        # 전세만
python apt_api.py --rent --top <N> --monthly       # 월세만

# 지역코드 목록
python apt_api.py --regions
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--rent` | 전월세 모드 (기본: 매매) |
| `--sync` | 데이터 동기화 |
| `--region CODE` | 지역코드 (예: 11170) |
| `--ym YYYYMM` | 년월 또는 범위 (예: 202511, 202501-202512) |
| `--stats` | DB 통계 출력 |
| `--search KEYWORD` | 아파트명/법정동 검색 |
| `--top N` | 고가 거래 TOP N |
| `--jeonse` | 전세만 조회 (--rent와 함께 사용) |
| `--monthly` | 월세만 조회 (--rent와 함께 사용) |
| `--regions` | 지역코드 목록 |
| `--limit N` | 조회 건수 제한 |
| `--output FILE` | 결과 저장 (json/csv) |

### `scripts/apt_meta_db.py`

**Purpose:** 메타DB 관리 (지역코드, 코드 참조)

**DB 위치:** `data/apt_meta.db`

**Usage:**
```bash
# CSV에서 지역코드 로드
python apt_meta_db.py --load-csv

# 지역코드 목록
python apt_meta_db.py --regions
python apt_meta_db.py --regions --sido "서울"

# 지역 검색
python apt_meta_db.py --search "강남"

# 시/도 목록
python apt_meta_db.py --sidos

# 메타DB 통계
python apt_meta_db.py --stats
```

### `scripts/apt_data_db.py`

**Purpose:** 데이터DB 관리 (거래 데이터, 동기화 상태)

**DB 위치:** `3_Resources/R-DB/outputs/apt.db`

**Usage:**
```bash
# DB 통계
python apt_data_db.py --stats

# 검색
python apt_data_db.py --search "한남더힐"

# 고가 거래
python apt_data_db.py --top 10
```

## 지역코드

전국 약 250개 시/군/구 지역코드가 `data/region_codes.csv`에 포함되어 있습니다.

### 지역 유형별 분포
| 유형 | 지역수 | 예시 |
|------|--------|------|
| 서울 | 25개 | 종로구, 중구, 용산구, 강남구 ... |
| 경기 | 42개 | 수원(4), 성남(3), 고양(3), 용인(3) ... |
| 광역시 | 49개 | 부산(16), 대구(8), 인천(10), 광주(5), 대전(5), 울산(5) |
| 세종 | 1개 | 세종시 |
| 도 | 133개 | 강원(18), 충북(14), 충남(16), 전북(15), 전남(22), 경북(24), 경남(22), 제주(2) |

### 주요 지역코드 (예시)
| 코드 | 지역 | 시도 | 유형 |
|------|------|------|------|
| 11110 | 종로구 | 서울 | 서울 |
| 11680 | 강남구 | 서울 | 서울 |
| 26350 | 해운대구 | 부산 | 광역시 |
| 41135 | 분당구 | 성남 | 경기 |
| 36110 | 세종시 | 세종 | 세종 |

### 지역코드 조회
```bash
# 전체 지역 목록
python .claude/skills/api-apt/scripts/apt_meta_db.py --regions

# 시도별 필터
python .claude/skills/api-apt/scripts/apt_meta_db.py --regions --sido "서울"

# 지역 검색
python .claude/skills/api-apt/scripts/apt_meta_db.py --search "강남"

# 시/도 목록
python .claude/skills/api-apt/scripts/apt_meta_db.py --sidos
```

## Examples

### Example 1: 용산구 최근 거래 조회
```bash
python .claude/skills/api-apt/scripts/apt_api.py --sync --region 11170 --ym 202511
python .claude/skills/api-apt/scripts/apt_api.py --top 10 --region 11170 --ym 202511
```

**출력:**
```
=== 고가 거래 TOP (서울 용산구) 2025년 11월 (10건) ===

순위 아파트명             동         면적    층   거래금액      거래일
---------------------------------------------------------------------------
1    한남더힐             한남동     233.06  4    1,277,000    2025-11-10
2    아스테리움용산       한강로2가  171.28  10   575,000      2025-11-10
3    신동아1              보광동     84.93   5    418,000      2025-11-30
...
```

### Example 2: 아파트 검색
```bash
python .claude/skills/api-apt/scripts/apt_api.py --search "래미안"
```

**출력:**
```
=== "래미안" 검색 결과 (25건) ===

아파트명             동         면적    층   거래금액      거래일
----------------------------------------------------------------------
래미안퍼스티지       반포동     84.92   15   430,000      2025-11-15
래미안원베일리       서초동     59.96   22   320,000      2025-11-10
...
```

### Example 3: Python 직접 사용
```python
from scripts.apt_api import AptTradeAPI

api = AptTradeAPI()

# 데이터 동기화
api.sync_region_month('11170', '202511')

# 검색
results = api.db.search('한남더힐')
for tx in results:
    print(f"{tx['apt_nm']}: {tx['deal_amount']}만원")

# 고가 거래
top_trades = api.db.get_top_trades(10, sgg_cd='11170')
for i, tx in enumerate(top_trades, 1):
    print(f"{i}. {tx['apt_nm']} - {tx['deal_amount_num']:,}만원")
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

| 응답 코드 | 원인 | 해결 |
|-----------|------|------|
| `000` / `00` | 정상 | - |
| `ERROR-300` | 인증키 오류 | API 키 확인 |
| `ERROR-310` | 요청제한 초과 | 호출 간격 조정 |
| `HTTP 400` | 잘못된 요청 | 파라미터 확인 |
| `HTTP 500` | 서버 오류 | 잠시 후 재시도 |

## Data Directory

### 파일 구조
```
.claude/skills/api-apt/
├── data/
│   ├── apt_meta.db          # 메타DB (지역코드, 코드 참조)
│   └── region_codes.csv     # 지역코드 마스터 데이터 (~250개 지역)
└── scripts/
    ├── apt_api.py           # API 클라이언트 + CLI
    ├── apt_meta_db.py       # 메타DB 관리 클래스
    └── apt_data_db.py       # 데이터DB 관리 클래스

3_Resources/R-DB/outputs/
└── apt.db                   # 데이터DB (거래 데이터)
```

### 메타DB 스키마 (data/apt_meta.db)
```sql
-- 지역코드 마스터
CREATE TABLE region_codes (
    region_cd TEXT PRIMARY KEY,   -- 5자리 법정동코드
    region_nm TEXT NOT NULL,      -- 구/시 명칭
    sido_nm TEXT,                 -- 시/도 명칭
    sido_cd TEXT,                 -- 시/도 코드 (2자리)
    region_type TEXT,             -- 서울/경기/광역시/도/세종
    updated_at TEXT
);

-- 거래유형 코드
CREATE TABLE dealing_codes (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

-- 동기화 로그
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY,
    sync_type TEXT,               -- regions/codes
    target TEXT,
    count INTEGER,
    synced_at TEXT
);
```

### 데이터DB 스키마 (3_Resources/R-DB/outputs/apt.db)
```sql
-- 아파트 매매 거래
CREATE TABLE apt_trades (
    id INTEGER PRIMARY KEY,
    sgg_cd TEXT,              -- 시군구코드
    umd_nm TEXT,              -- 법정동명
    apt_seq TEXT,             -- 아파트 일련번호
    apt_nm TEXT,              -- 아파트명
    build_year INTEGER,       -- 건축년도
    deal_year INTEGER,        -- 거래년도
    deal_month INTEGER,       -- 거래월
    deal_day INTEGER,         -- 거래일
    deal_amount TEXT,         -- 거래금액 (원본)
    deal_amount_num INTEGER,  -- 거래금액 (만원)
    exclu_use_ar REAL,        -- 전용면적 (㎡)
    floor INTEGER,            -- 층
    UNIQUE(apt_seq, deal_year, deal_month, deal_day, floor, exclu_use_ar)
);

-- 아파트 전월세 거래
CREATE TABLE apt_rents (
    id INTEGER PRIMARY KEY,
    sgg_cd TEXT,              -- 시군구코드
    umd_nm TEXT,              -- 법정동명
    apt_nm TEXT,              -- 아파트명
    build_year INTEGER,       -- 건축년도
    deal_year INTEGER,        -- 거래년도
    deal_month INTEGER,       -- 거래월
    deal_day INTEGER,         -- 거래일
    deposit INTEGER,          -- 보증금 (만원)
    monthly_rent INTEGER,     -- 월세 (만원, 0=전세)
    exclu_use_ar REAL,        -- 전용면적 (㎡)
    floor INTEGER,            -- 층
    contract_type TEXT,       -- 계약유형 (신규/갱신)
    UNIQUE(sgg_cd, apt_nm, deal_year, deal_month, deal_day, floor, exclu_use_ar, deposit, monthly_rent)
);

-- 매매 동기화 상태
CREATE TABLE sync_status (
    sgg_cd TEXT,
    deal_ym TEXT,
    total_count INTEGER,
    synced_at DATETIME,
    PRIMARY KEY (sgg_cd, deal_ym)
);

-- 전월세 동기화 상태
CREATE TABLE rent_sync_status (
    sgg_cd TEXT,
    deal_ym TEXT,
    total_count INTEGER,
    synced_at DATETIME,
    PRIMARY KEY (sgg_cd, deal_ym)
);
```

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-apt >> scripts >> apt_api.py`
- 메타DB: `.claude >> skills >> api-apt >> data >> apt_meta.db`
- 데이터DB: `3_Resources >> R-DB >> outputs >> apt.db`
- 지역CSV: `.claude >> skills >> api-apt >> data >> region_codes.csv`

## Limitations

- 일일 API 호출 제한: 10,000건 (개발계정)
- 페이지당 최대 조회: 1,000건
- 데이터 제공 범위: 2006년 1월 이후

## See Also

- [공공데이터포털 API](https://www.data.go.kr/data/15126468/openapi.do)
- `api-ecos` 스킬: 한국은행 경제통계
- `api-fisis` 스킬: 금융감독원 금융통계
- `api-dart` 스킬: 전자공시시스템
