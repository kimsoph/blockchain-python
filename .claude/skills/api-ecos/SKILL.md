# -*- coding: utf-8 -*-
---
name: api-ecos
description: 한국은행 경제통계시스템(ECOS) OpenAPI를 통해 국내외 경제통계 데이터를 조회하는 스킬. 기준금리, 환율, 물가지수, 고용률 등 100대 통계지표 및 다양한 경제통계 수집에 활용.
version: 1.0.0
---

# ECOS OpenAPI Skill

## Purpose

한국은행 경제통계시스템(ECOS) OpenAPI를 통해 국내외 경제통계 데이터를 조회합니다.

**핵심 기능:**
1. 통계표 검색: 통계표 목록 및 항목 조회
2. 통계 데이터 조회: 기간별/주기별 경제지표 조회
3. 100대 통계지표: 주요 경제지표 실시간 조회
4. 메타데이터 DB: 통계표/항목 정보 SQLite 관리

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 한국은행 기준금리, 시장금리를 조회할 때
- 환율, 물가지수, 고용률 등 경제지표가 필요할 때
- 국제수지, 수출입 통계를 분석할 때
- 시계열 경제 데이터를 수집할 때

트리거 예시:
- "현재 기준금리 알려줘"
- "2024년 월별 소비자물가지수 조회해줘"
- "한국은행 100대 통계지표 보여줘"
- "달러 환율 추이 가져와줘"

## API 개요

### Base URL
```
http://ecos.bok.or.kr/api/
```

### URL 구조
```
http://ecos.bok.or.kr/api/{서비스명}/{인증키}/{요청타입}/{언어}/{시작건수}/{종료건수}/{파라미터들}
```

### 인증
- API Key 방식 (URL 경로 파라미터)
- 인증키는 [한국은행 Open API 서비스](https://ecos.bok.or.kr/api/)에서 신청
- 환경변수: `ECOS_API_KEY`

### 주요 API 엔드포인트

| 서비스명 | 설명 | 용도 |
|----------|------|------|
| `StatisticTableList` | 통계표 목록 | 통계표 검색 |
| `StatisticItemList` | 통계 항목 목록 | 항목 조회 |
| `StatisticSearch` | 통계 데이터 조회 | 데이터 수집 |
| `KeyStatisticList` | 100대 통계지표 | 주요지표 |
| `StatisticWord` | 통계용어사전 | 용어 검색 |

### 주기 코드

| 코드 | 설명 |
|------|------|
| A | 년 (Annual) |
| S | 반년 (Semi-annual) |
| Q | 분기 (Quarterly) |
| M | 월 (Monthly) |
| SM | 반월 (Semi-monthly) |
| D | 일 (Daily) |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
ECOS_API_KEY=your_api_key_here
```

## Workflow

### Step 1: 메타데이터 DB 동기화
```bash
# 통계표 목록 + 100대 지표 동기화
python .claude/skills/api-ecos/scripts/ecos_api.py --sync

# 강제 재동기화
python .claude/skills/api-ecos/scripts/ecos_api.py --sync --force

# DB 통계 확인
python .claude/skills/api-ecos/scripts/ecos_api.py --stats
```

### Step 2: 통계표 검색
```bash
# 키워드로 통계표 검색
python .claude/skills/api-ecos/scripts/ecos_api.py --search "금리"

# 통계표 전체 목록
python .claude/skills/api-ecos/scripts/ecos_api.py --tables
```

### Step 3: 항목 조회
```bash
# 특정 통계표의 항목 목록
python .claude/skills/api-ecos/scripts/ecos_api.py --items 722Y001
```

### Step 4: 데이터 조회
```bash
# 기준금리 월별 데이터 (2024년)
python .claude/skills/api-ecos/scripts/ecos_api.py \
    --stat-code 722Y001 --cycle M --start 202401 --end 202412

# 소비자물가지수 연간 데이터
python .claude/skills/api-ecos/scripts/ecos_api.py \
    --stat-code 064Y001 --cycle A --start 2020 --end 2024

# 100대 통계지표
python .claude/skills/api-ecos/scripts/ecos_api.py --key-stats
```

### Step 5: 결과 저장
```bash
# CSV 파일로 저장
python .claude/skills/api-ecos/scripts/ecos_api.py \
    --stat-code 722Y001 --cycle M --start 202401 --end 202412 \
    --output result.csv

# JSON 파일로 저장
python .claude/skills/api-ecos/scripts/ecos_api.py \
    --stat-code 722Y001 --cycle M --start 202401 --end 202412 \
    --output result.json
```

## Scripts Reference

### `scripts/ecos_api.py`

**Purpose:** ECOS OpenAPI 호출 및 데이터 처리

**Usage:**
```bash
# 메타데이터 동기화
python ecos_api.py --sync [--force]

# DB 통계
python ecos_api.py --stats

# 통계표 검색
python ecos_api.py --search <키워드>

# 통계표 목록
python ecos_api.py --tables

# 항목 목록
python ecos_api.py --items <통계코드>

# 데이터 조회
python ecos_api.py --stat-code <코드> --cycle <주기> --start <시작일> --end <종료일>

# 100대 지표
python ecos_api.py --key-stats

# 용어 검색
python ecos_api.py --word <키워드>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--sync` | 메타데이터 DB 동기화 |
| `--force` | 강제 동기화 |
| `--stats` | DB 통계 출력 |
| `--search KEYWORD` | 통계표 검색 |
| `--tables` | 통계표 목록 조회 |
| `--items CODE` | 항목 목록 조회 |
| `--stat-code CODE` | 통계표 코드 |
| `--cycle A/S/Q/M/SM/D` | 주기 |
| `--start DATE` | 시작일 (YYYYMMDD 또는 YYYY) |
| `--end DATE` | 종료일 |
| `--item-code CODE` | 항목코드 |
| `--key-stats` | 100대 통계지표 |
| `--word KEYWORD` | 통계용어 검색 |
| `--limit N` | 조회 건수 |
| `--output FILE` | 결과 저장 (json/csv) |

### `scripts/ecos_meta_db.py`

**Purpose:** 메타데이터 SQLite DB 관리

**Usage:**
```bash
# DB 초기화
python ecos_meta_db.py --init

# 통계표 목록 동기화
python ecos_meta_db.py --sync-tables [--force]

# 특정 통계표 항목 동기화
python ecos_meta_db.py --sync-items <통계코드>

# 100대 지표 동기화
python ecos_meta_db.py --sync-key

# 전체 동기화
python ecos_meta_db.py --sync-all

# 통계표 검색
python ecos_meta_db.py --search <키워드>

# 항목 검색
python ecos_meta_db.py --search-items <키워드>

# 통계표 정보
python ecos_meta_db.py --info <통계코드>

# 항목 목록
python ecos_meta_db.py --items <통계코드>

# DB 통계
python ecos_meta_db.py --stats
```

## 주요 통계표 코드

| 코드 | 통계명 | 주기 |
|------|--------|------|
| 722Y001 | 한국은행 기준금리 | M |
| 721Y001 | 시장금리(일별) | D |
| 731Y003 | 주요국 금리 | M |
| 200Y001 | 주요 경제지표 | A |
| 601Y002 | 국제수지 | M |
| 901Y014 | 주요국 환율 | D |
| 064Y001 | 소비자물가지수 | M |
| 104Y016 | 고용률 | M |
| 111Y002 | 생산지수 | M |
| 501Y001 | 수출입 | M |

## Examples

### Example 1: 기준금리 조회
```bash
# 2024년 월별 기준금리
python .claude/skills/api-ecos/scripts/ecos_api.py \
    --stat-code 722Y001 --cycle M --start 202401 --end 202412
```

**출력:**
```
=== [722Y001] 한국은행 기준금리 (12건) ===
기간: 202401 ~ 202412 (주기: 월)
시점         항목명                              값                   단위
--------------------------------------------------------------------------------
202412      한국은행 기준금리                   3.00                 연%
202411      한국은행 기준금리                   3.25                 연%
...
```

### Example 2: 100대 통계지표
```bash
python .claude/skills/api-ecos/scripts/ecos_api.py --key-stats
```

**출력:**
```
=== 100대 통계지표 (100건) ===
분류            지표명                              값              단위       시점
------------------------------------------------------------------------------------------
국민소득        국내총생산(GDP)                     2,401.0         조원       2024
물가            소비자물가지수                      114.2           2020=100   202411
금리            한국은행 기준금리                   3.00            연%        202412
...
```

### Example 3: Python 직접 사용
```python
from scripts.ecos_api import EcosAPI

api = EcosAPI()

# 기준금리 조회
result = api.get_statistic_search(
    stat_code="722Y001",
    cycle="M",
    start_date="202401",
    end_date="202412"
)

for item in result.get('StatisticSearch', {}).get('row', []):
    print(f"{item['TIME']}: {item['DATA_VALUE']}%")

# 100대 통계지표
key_stats = api.get_key_statistic_list()
for item in key_stats.get('KeyStatisticList', {}).get('row', []):
    print(f"{item['ITEM_NAME']}: {item['DATA_VALUE']} {item['UNIT_NAME']}")
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

| 오류 코드 | 원인 | 해결 |
|-----------|------|------|
| `INFO-000` | 정상 | - |
| `ERROR-300` | 인증키 오류 | API 키 확인 |
| `ERROR-301` | 등록되지 않은 인증키 | 키 등록 확인 |
| `ERROR-310` | 요청제한 초과 | 호출 간격 조정 |
| `ERROR-331` | 부적절한 요청 | 파라미터 확인 |
| `ERROR-500` | 서버 오류 | 잠시 후 재시도 |

## Data Directory

### 데이터 파일 위치
```
.claude/skills/api-ecos/data/
├── ecos_meta.db         # 메타데이터 SQLite DB
└── (output files)       # 조회 결과 저장
```

### 메타데이터 DB 스키마
```sql
-- 통계표 목록
CREATE TABLE stat_tables (
    id INTEGER PRIMARY KEY,
    p_stat_code TEXT,        -- 상위통계표코드
    stat_code TEXT UNIQUE,   -- 통계표코드
    stat_name TEXT,          -- 통계명
    cycle TEXT,              -- 주기
    srch_yn TEXT,            -- 검색가능여부
    org_name TEXT,           -- 출처
    updated_at TEXT
);

-- 통계 항목
CREATE TABLE stat_items (
    stat_code TEXT,          -- 통계표코드
    grp_code TEXT,           -- 항목그룹코드
    grp_name TEXT,           -- 항목그룹명
    item_code TEXT,          -- 항목코드
    item_name TEXT,          -- 항목명
    unit_name TEXT,          -- 단위
    ...
);

-- 100대 통계지표
CREATE TABLE key_statistics (
    class_code TEXT,         -- 분류코드
    class_name TEXT,         -- 분류명
    stat_name TEXT,          -- 통계명
    item_name TEXT,          -- 항목명
    data_value TEXT,         -- 최신값
    unit_name TEXT,          -- 단위
    time TEXT,               -- 시점
    ...
);
```

### 메타데이터 DB 관리
- 최초 실행 시 `--sync`로 동기화
- 통계표 목록: 1일 이내 재동기화 스킵
- 100대 지표: 6시간 이내 재동기화 스킵
- `--sync --force`로 강제 갱신
- FTS5 전문 검색 지원

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-ecos >> scripts >> ecos_api.py`
- 데이터: `.claude >> skills >> api-ecos >> data >> ecos_meta.db`

## Limitations

- 일일 API 호출 제한: 100,000건
- 1회 최대 조회: 100,000건
- 인증키 발급 후 익일부터 사용 가능
- 일부 통계표는 특정 주기만 지원

## See Also

- [한국은행 Open API 서비스](https://ecos.bok.or.kr/api/)
- [PublicDataReader](https://github.com/WooilJeong/PublicDataReader) - Python 라이브러리
- `api-dart` 스킬: DART 전자공시시스템
- `api-fisis` 스킬: FISIS 금융통계정보시스템
- `md2db` 스킬: 분석 결과 DB 저장
