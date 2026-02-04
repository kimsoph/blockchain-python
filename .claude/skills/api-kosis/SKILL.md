# -*- coding: utf-8 -*-
---
name: api-kosis
description: 국가통계포털(KOSIS) OpenAPI를 통해 국가통계 데이터를 조회하는 스킬. 인구, 경제, 물가, 고용, 주택, 환경 등 다양한 분야의 통계 데이터 수집에 활용.
version: 2.0.0
---

# KOSIS OpenAPI Skill

## Purpose

국가통계포털(KOSIS) OpenAPI를 통해 국가통계 데이터를 조회합니다.

**핵심 기능:**
1. 통합검색: 통계표 검색
2. 통계목록: 계층구조 조회
3. 통계자료: 실제 데이터 조회
4. 통계설명: 메타정보 조회
5. 메타데이터 DB: 통계표 정보 SQLite 관리

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 인구, 경제, 물가, 고용 등 국가통계를 조회할 때
- 시도별/시군구별 지역통계가 필요할 때
- 시계열 통계 데이터를 수집할 때
- 북한 또는 국제 통계를 조회할 때

트리거 예시:
- "한국 인구 통계 조회해줘"
- "2024년 월별 실업률 가져와"
- "서울시 주택 가격 통계 조회"
- "소비자물가지수 추이 보여줘"

## API 개요

### Base URL
```
https://kosis.kr/openapi/
```

### 주요 엔드포인트

| 엔드포인트 | 설명 | 용도 |
|------------|------|------|
| `statisticsSearch.do` | 통합검색 | 통계표 검색 |
| `statisticsList.do` | 통계목록 | 계층구조 조회 |
| `Param/statisticsParameterData.do` | 통계자료 | 데이터 조회 |
| `statisticsData.do` | 통계설명 | 메타정보 |
| `statisticsTableData.do` | 통계표설명 | 상세정보 |

### 인증
- API Key 방식 (Query Parameter)
- 인증키는 [KOSIS 공유서비스](https://kosis.kr/openapi/)에서 신청
- 환경변수: `KOSIS_API_KEY`

### 서비스뷰 코드

| 코드 | 설명 |
|------|------|
| MT_ZTITLE | 국내통계 주제별 |
| MT_OTITLE | 국내통계 기관별 |
| MT_GTITLE01 | e-지방지표 시도별 |
| MT_GTITLE02 | e-지방지표 시군구별 |
| MT_ATITLE01 | 북한통계 주제별 |
| MT_BTITLE | 국제통계 |

### 수록주기 코드

| 코드 | 설명 |
|------|------|
| Y | 년 (Yearly) |
| H | 반년 (Half-yearly) |
| Q | 분기 (Quarterly) |
| M | 월 (Monthly) |
| S | 반월 (Semi-monthly) |
| D | 일 (Daily) |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
KOSIS_API_KEY=your_api_key_here
```

## Workflow

### Step 1: 메타데이터 DB 동기화
```bash
# 기본 키워드로 동기화 (인구, 경제, 물가, 고용, 주택, 환경)
python .claude/skills/api-kosis/scripts/kosis_api.py --sync

# 강제 재동기화
python .claude/skills/api-kosis/scripts/kosis_api.py --sync --force

# DB 통계 확인
python .claude/skills/api-kosis/scripts/kosis_api.py --stats
```

### Step 2: 통계표 검색
```bash
# KOSIS 통합검색
python .claude/skills/api-kosis/scripts/kosis_api.py --search "실업률"

# 메타DB 검색
python .claude/skills/api-kosis/scripts/kosis_api.py --db-search "인구"

# 통계목록 조회
python .claude/skills/api-kosis/scripts/kosis_api.py --list MT_ZTITLE A
```

### Step 3: 통계표 정보 확인
```bash
# 통계표 정보 조회
python .claude/skills/api-kosis/scripts/kosis_api.py --info DT_1IN1502
```

### Step 4: 데이터 조회
```bash
# 기간 지정 조회 (2023년 월별)
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1IN1502 --prd-se M --start 202301 --end 202312

# 최근 N개 시점 조회
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1IN1502 --prd-se M --recent 12

# 연간 데이터 조회
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1B8000G --prd-se Y --start 2019 --end 2023
```

### Step 5: 결과 저장
```bash
# CSV 파일로 저장
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1IN1502 --prd-se M --recent 12 \
    --output result.csv

# JSON 파일로 저장
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1IN1502 --prd-se M --recent 12 \
    --output result.json
```

## 분류정보 조회 및 스마트 모드 (v2.0 신규)

### 문제 해결

KOSIS API는 통계표마다 분류 구조가 다르며(1~8단계), `objL1='ALL'`이 모든 통계표에서 작동하지 않습니다. 이로 인해 조회 오류가 빈번하게 발생합니다.

v2.0에서 추가된 기능:
1. **분류정보 조회**: 통계표의 분류/항목 구조를 API로 조회하여 DB에 저장
2. **스마트 모드**: 분류 구조를 자동 확인하고 적절한 파라미터로 조회
3. **친절한 오류 안내**: 오류 발생 시 분류 구조와 권장 명령어 제시

### Step 6: 분류정보 조회
```bash
# 통계표의 분류/항목 정보 조회 (DB에 저장됨)
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --cls-info 101 DT_1B040A3

# 강제 재조회 (캐시 무시)
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --cls-info 101 DT_1B040A3 --force
```

**출력 예시:**
```
=== [DT_1B040A3] 분류/항목 정보 ===
분류 단계 수: 2
항목 수: 5
DB 저장: 25건

분류 구조:
  objL1: 행정구역별
    값(17개): 00(전국) 11(서울) 21(부산) 22(대구) ... 외 9개
  objL2: 성별
    값(3개): 0(계) 1(남자) 2(여자)

항목 목록(5개):
  - T1: 총인구 (명)
  - T2: 내국인 (명)
  ...

추천 파라미터:
  --obj-l1 00
  --obj-l2 0
  --itm-id ALL
```

### Step 7: 스마트 모드 조회
```bash
# 스마트 모드 (분류 자동 처리)
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1B040A3 --prd-se Y --start 2020 --end 2023 --smart

# 일부 파라미터 지정 + 스마트 모드
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1B040A3 --prd-se Y --start 2020 --end 2023 \
    --obj-l1 11 --smart
```

**스마트 모드 동작:**
1. 분류 구조 확인 (DB 우선, 없으면 API 호출)
2. 누락된 분류 파라미터에 기본값 자동 설정
3. 대용량(40,000셀 초과) 예상 시 경고
4. 조회 실행

### Step 8: 다단계 분류 지정
```bash
# objL1~L8 직접 지정
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1B040A3 --prd-se Y --start 2020 --end 2023 \
    --obj-l1 00 --obj-l2 0 --itm-id ALL
```

## Scripts Reference

### `scripts/kosis_api.py`

**Purpose:** KOSIS OpenAPI 호출 및 데이터 처리

**Usage:**
```bash
# 메타데이터 동기화
python kosis_api.py --sync [--force]

# DB 통계
python kosis_api.py --stats

# 통합검색
python kosis_api.py --search <키워드>

# 메타DB 검색
python kosis_api.py --db-search <키워드>

# 통계목록 조회
python kosis_api.py --list [VW_CD] [PARENT_ID]

# 통계표 정보
python kosis_api.py --info <통계표ID>

# 데이터 조회
python kosis_api.py --data <기관ID> <통계표ID> --prd-se <주기> --start <시작> --end <종료>
python kosis_api.py --data <기관ID> <통계표ID> --prd-se <주기> --recent <N>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--sync` | 메타데이터 DB 동기화 |
| `--force` | 강제 동기화 |
| `--stats` | DB 통계 출력 |
| `--search KEYWORD` | KOSIS 통합검색 |
| `--db-search KEYWORD` | 메타DB 검색 |
| `--list [VW_CD] [PARENT_ID]` | 통계목록 조회 |
| `--info TBL_ID` | 통계표 정보 |
| `--cls-info ORG_ID TBL_ID` | 분류/항목 정보 조회 (v2.0) |
| `--data ORG_ID TBL_ID` | 통계자료 조회 |
| `--prd-se Y/H/Q/M/S/D` | 수록주기 |
| `--start DATE` | 시작 시점 (YYYY 또는 YYYYMM) |
| `--end DATE` | 종료 시점 |
| `--recent N` | 최근 N개 시점 |
| `--itm-id ID` | 항목 ID (기본: ALL) |
| `--obj-l1` ~ `--obj-l8` | 분류1~8 (v2.0) |
| `--smart` | 스마트 모드 - 분류 자동 처리 (v2.0) |
| `--limit N` | 조회 건수 |
| `--output FILE` | 결과 저장 (json/csv) |

### `scripts/kosis_meta_db.py`

**Purpose:** 메타데이터 SQLite DB 관리

**Usage:**
```bash
# DB 초기화
python kosis_meta_db.py --init

# 검색 기반 동기화
python kosis_meta_db.py --sync-search "인구,경제,물가"

# 계층구조 동기화 (루트에서 시작, 빈 문자열 사용)
python kosis_meta_db.py --sync-hierarchy MT_ZTITLE ""

# 계층구조 동기화 (깊이 제한)
python kosis_meta_db.py --sync-hierarchy MT_ZTITLE "" --max-depth 2

# 전체 동기화
python kosis_meta_db.py --sync-all

# 통계표 검색
python kosis_meta_db.py --search <키워드>

# 통계표 정보
python kosis_meta_db.py --info <통계표ID>

# DB 통계
python kosis_meta_db.py --stats
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--init` | DB 초기화 |
| `--sync-search KEYWORDS` | 키워드로 통계표 검색 후 동기화 (쉼표 구분) |
| `--sync-hierarchy VW_CD PARENT_ID` | 계층구조 동기화 (루트는 빈 문자열) |
| `--max-depth N` | 계층구조 최대 탐색 깊이 (기본값: 3) |
| `--sync-all` | 전체 동기화 (검색 + 계층구조) |
| `--force` | 강제 동기화 (캐시 무시) |
| `--search KEYWORD` | 통계표 검색 |
| `--info TBL_ID` | 통계표 정보 조회 |
| `--hierarchy [VW_CD]` | 계층구조 조회 |
| `--stats` | DB 통계 출력 |
| `--db PATH` | DB 파일 경로 지정 |

## 주요 통계표 코드

| 기관ID | 통계표ID | 통계명 | 주기 |
|--------|----------|--------|------|
| 101 | DT_1IN1502 | 시도별 인구 | M |
| 101 | DT_1B8000G | 사망원인통계 | Y |
| 110 | DT_11001N_2015 | 소비자물가지수 | M |
| 118 | DT_118N_MON002 | 실업률 | M |
| 116 | DT_MLTM_2086 | 미분양 현황 | M |
| 380 | DT_M102 | 주택매매가격지수 | M |

## Examples

### Example 1: 인구 통계 조회
```bash
# 시도별 인구 (최근 12개월)
python .claude/skills/api-kosis/scripts/kosis_api.py \
    --data 101 DT_1IN1502 --prd-se M --recent 12
```

**출력:**
```
=== [DT_1IN1502] 주민등록인구현황 (12건) ===
시점         분류                      항목                      값              단위
-------------------------------------------------------------------------------------------------
202412      전국                      인구(명)                  51,234,567      명
202411      전국                      인구(명)                  51,245,678      명
...
```

### Example 2: 통합검색
```bash
python .claude/skills/api-kosis/scripts/kosis_api.py --search "실업률"
```

**출력:**
```
=== '실업률' 검색 결과 (25건) ===
통계표ID              통계표명                                  기관명
--------------------------------------------------------------------------------
DT_118N_MON002       경제활동인구조사 실업률                   통계청
DT_118N_MON004       실업자 및 실업률                         통계청
...
```

### Example 3: Python 직접 사용
```python
from scripts.kosis_api import KosisAPI

api = KosisAPI()

# 통합검색
result = api.search("실업률")
for item in result[:5]:
    print(f"{item['TBL_ID']}: {item['TBL_NM']}")

# 통계자료 조회
data = api.get_stat_data(
    org_id="118",
    tbl_id="DT_118N_MON002",
    prd_se="M",
    start_prd_de="202301",
    end_prd_de="202312"
)

for item in data:
    print(f"{item['PRD_DE']}: {item['DT']}%")
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
| `HTTP 401` | 인증키 오류 | API 키 확인 |
| `HTTP 403` | 권한 없음 | 키 등록 확인 |
| `TIMEOUT` | 요청 시간 초과 | 잠시 후 재시도 |
| `err: API 키가 설정되지 않음` | 환경변수 미설정 | .env 파일 확인 |

## Data Directory

### 데이터 파일 위치
```
.claude/skills/api-kosis/data/
├── kosis_meta.db        # 메타데이터 SQLite DB
└── (output files)       # 조회 결과 저장
```

### 메타데이터 DB 스키마
```sql
-- 통계표 목록
CREATE TABLE stat_tables (
    id INTEGER PRIMARY KEY,
    tbl_id TEXT UNIQUE,        -- 통계표 ID
    tbl_nm TEXT,               -- 통계표명
    org_id TEXT,               -- 기관 ID
    org_nm TEXT,               -- 기관명
    stat_nm TEXT,              -- 통계명
    prd_se TEXT,               -- 수록주기
    prd_de TEXT,               -- 수록시점
    updated_at TEXT
);

-- 통계목록 계층구조
CREATE TABLE stat_hierarchy (
    vw_cd TEXT,                -- 서비스뷰 코드
    list_id TEXT,              -- 목록 ID
    list_nm TEXT,              -- 목록명
    parent_list_id TEXT,       -- 상위 목록 ID
    tbl_id TEXT,               -- 통계표 ID
    rec_tbl_se TEXT,           -- 목록유형 (T:통계표, G:그룹)
    ...
);
```

### 메타데이터 DB 관리
- 최초 실행 시 `--sync`로 동기화
- 통계표 목록: 1일 이내 재동기화 스킵
- `--sync --force`로 강제 갱신
- FTS5 전문 검색 지원

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-kosis >> scripts >> kosis_api.py`
- 데이터: `.claude >> skills >> api-kosis >> data >> kosis_meta.db`

## Limitations

- 일일 API 호출 제한: 1,000회 (개발계정)
- 1회 최대 조회: 약 10,000건
- 인증키 발급 후 즉시 사용 가능
- 일부 통계표는 특정 주기만 지원
- 대용량 데이터는 대용량통계자료 API 사용 권장

## See Also

- [KOSIS 공유서비스](https://kosis.kr/openapi/)
- [KOSIS 개발 가이드](https://kosis.kr/openapi/devGuide/devGuide_0101List.do)
- [PublicDataReader](https://github.com/WooilJeong/PublicDataReader) - Python 라이브러리
- `api-ecos` 스킬: 한국은행 ECOS 경제통계
- `api-fisis` 스킬: FISIS 금융통계정보시스템
- `api-dart` 스킬: DART 전자공시시스템
