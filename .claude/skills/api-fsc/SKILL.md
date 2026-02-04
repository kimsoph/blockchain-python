# -*- coding: utf-8 -*-
---
name: api-fsc
description: 금융위원회 국내은행정보 API를 통해 국내 은행의 일반현황, 재무현황, 경영지표, 영업활동 정보를 조회하는 스킬. 은행별 시계열 데이터 수집 및 비교 분석에 활용.
version: 1.0.0
---

# 금융위원회 국내은행정보 API Skill

## Purpose

금융위원회 국내은행정보 API를 통해 국내 은행의 각종 통계 데이터를 조회합니다.

**핵심 기능:**
1. **일반현황** 조회: 설립년도, 점포수, 임직원수
2. **재무현황** 조회: 자산, 부채, 자본
3. **경영지표** 조회: ROA, ROE, NIM, BIS비율
4. **영업활동** 조회: 대출금, 예수금

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 국내 은행의 재무현황을 조회할 때
- 은행별 경영지표(ROA, ROE)를 비교할 때
- 특정 기간의 은행 영업활동 데이터가 필요할 때
- 은행 일반현황(점포수, 임직원)을 확인할 때

트리거 예시:
- "IBK기업은행 경영지표 조회해줘"
- "신한은행 재무현황 가져와줘"
- "국내 은행 ROE 비교해줘"
- "2024년 12월 은행별 자산 현황"

## API 개요

### Base URL
```
https://apis.data.go.kr/1160100/service/GetDomeBankInfoService
```

### 4개 오퍼레이션

| 오퍼레이션 | 설명 | 주요 항목 |
|-----------|------|----------|
| `getDomeBankGeneInfo` | 일반현황 | 설립년도, 점포수, 임직원수 |
| `getDomeBankFinaInfo` | 재무현황 | 자산, 부채, 자본 |
| `getDomeBankKeyManaIndi` | 경영지표 | ROA, ROE, NIM, BIS비율 |
| `getDomeBankMajoBusiActi` | 영업활동 | 대출금, 예수금 |

### 인증
- Query 파라미터: `serviceKey={API_KEY}`
- 환경변수: `FSC_API_KEY`

### 공통 파라미터

| 파라미터 | 필수 | 설명 | 예시 |
|----------|------|------|------|
| `serviceKey` | O | API 인증키 | - |
| `pageNo` | O | 페이지 번호 | 1 |
| `numOfRows` | O | 페이지당 건수 | 100 |
| `resultType` | X | 응답형식 | json |
| `basYm` | X | 기준년월 | 202412 |
| `fncoNm` | X | 은행명 | IBK기업은행 |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
FSC_API_KEY=your_api_key_here
```

### API 활용신청
1. [공공데이터포털](https://www.data.go.kr/) 접속 및 로그인
2. "금융위원회_금융통계국내은행정보" 검색
3. 활용신청 (자동승인)

## Workflow

### Step 1: 데이터 동기화
```bash
# 경영지표 전체 은행 동기화
python .claude/skills/api-fsc/scripts/fsc_api.py --sync --type metrics --ym 202412

# 특정 은행만 동기화
python .claude/skills/api-fsc/scripts/fsc_api.py --sync --type finance --bank "IBK기업은행" --ym 202412

# 기간 범위 동기화
python .claude/skills/api-fsc/scripts/fsc_api.py --sync --type metrics --ym 202401-202412
```

### Step 2: 데이터 조회
```bash
# 경영지표 조회
python .claude/skills/api-fsc/scripts/fsc_api.py --metrics --bank "신한은행" --ym 202412

# 재무현황 조회
python .claude/skills/api-fsc/scripts/fsc_api.py --finance --bank "IBK기업은행" --ym 202412

# 일반현황 조회
python .claude/skills/api-fsc/scripts/fsc_api.py --general --ym 202412
```

### Step 3: 분석
```bash
# 은행간 ROE 비교
python .claude/skills/api-fsc/scripts/fsc_api.py --compare --metric ROE --ym 202412

# 자산 상위 10개 은행
python .claude/skills/api-fsc/scripts/fsc_api.py --top 10 --by assets --ym 202412

# DB 통계
python .claude/skills/api-fsc/scripts/fsc_api.py --stats
```

### Step 4: 결과 저장
```bash
python .claude/skills/api-fsc/scripts/fsc_api.py --compare --metric ROE --ym 202412 --output result.csv
```

## Scripts Reference

### `scripts/fsc_api.py`

**Purpose:** FSC API 호출 + 데이터DB 관리 + CLI

**Options:**

| 옵션 | 설명 |
|------|------|
| `--sync` | 데이터 동기화 |
| `--type TYPE` | 데이터 유형 (general/finance/metrics/business) |
| `--bank NAME` | 은행명 필터 |
| `--ym YYYYMM` | 기준년월 또는 범위 (YYYYMM-YYYYMM) |
| `--general` | 일반현황 조회 |
| `--finance` | 재무현황 조회 |
| `--metrics` | 경영지표 조회 |
| `--business` | 영업활동 조회 |
| `--compare` | 은행간 지표 비교 |
| `--metric CODE` | 비교 지표 (ROA/ROE/NIM/BIS/NPL/LDR) |
| `--banks` | 은행 목록 (메타DB) |
| `--search KEYWORD` | 은행 검색 |
| `--top N` | 상위 N개 은행 |
| `--by FIELD` | 정렬 기준 (assets/equity/loans/deposits) |
| `--stats` | DB 통계 |
| `--output FILE` | 결과 저장 (json/csv) |

### `scripts/fsc_meta_db.py`

**Purpose:** 메타DB 관리 (은행 마스터, 코드 참조)

**Options:**

| 옵션 | 설명 |
|------|------|
| `--banks` | 은행 목록 |
| `--bank-type TYPE` | 은행 유형 필터 |
| `--search KEYWORD` | 은행 검색 |
| `--types` | 데이터 유형 목록 |
| `--metrics` | 경영지표 코드 목록 |
| `--stats` | 메타DB 통계 |

## 국내 주요 은행

### 시중은행
| 은행명 | 금융지주 |
|--------|---------|
| KB국민은행 | KB금융지주 |
| 신한은행 | 신한금융지주 |
| 하나은행 | 하나금융지주 |
| 우리은행 | 우리금융지주 |

### 특수은행
| 은행명 | 비고 |
|--------|------|
| IBK기업은행 | 국책은행 |
| NH농협은행 | 농협금융지주 |
| KDB산업은행 | 국책은행 |
| 한국수출입은행 | 국책은행 |

### 지방은행
| 은행명 | 금융지주 |
|--------|---------|
| DGB대구은행 | DGB금융지주 |
| BNK부산은행 | BNK금융지주 |
| 광주은행 | JB금융지주 |

## Examples

### Example 1: 경영지표 동기화 및 조회
```bash
python .claude/skills/api-fsc/scripts/fsc_api.py --sync --type metrics --ym 202412
python .claude/skills/api-fsc/scripts/fsc_api.py --metrics --bank "IBK기업은행" --ym 202412
```

**출력:**
```
=== 경영지표 (1건) ===
은행명               기준월   ROA     ROE     NIM     BIS
-----------------------------------------------------------------
IBK기업은행          202412   0.48%   7.82%   1.72%   16.45%
```

### Example 2: 은행간 ROE 비교
```bash
python .claude/skills/api-fsc/scripts/fsc_api.py --compare --metric ROE --ym 202412
```

**출력:**
```
=== 은행별 자기자본순이익률 비교 (2024년 12월) ===
순위   은행명                    ROE
---------------------------------------------
1      KB국민은행                9.15%
2      신한은행                  8.92%
3      하나은행                  8.56%
4      우리은행                  8.21%
5      IBK기업은행               7.82%
```

### Example 3: Python 직접 사용
```python
from scripts.fsc_api import FscAPI

api = FscAPI()

# 데이터 동기화
api.sync_data('metrics', '202412')

# DB에서 조회
results = api.data_db.get_metrics('IBK기업은행', '202412')
for r in results:
    print(f"{r['bank_nm']}: ROE {r['roe']}%")

# 은행간 비교
comparison = api.data_db.compare_banks('ROE', '202412')
for i, b in enumerate(comparison, 1):
    print(f"{i}. {b['bank_nm']}: {b['value']:.2f}%")

api.close()
```

## Error Handling

| 응답 코드 | 원인 | 해결 |
|-----------|------|------|
| `00` | 정상 | - |
| `01` | 인증키 오류 | API 키 확인 |
| `02` | 요청제한 초과 | 호출 간격 조정 |
| `10` | 잘못된 요청 | 파라미터 확인 |
| `30` | 데이터 없음 | 기준년월 확인 |

## Data Directory

### 파일 위치
```
.claude/skills/api-fsc/
├── data/
│   └── fsc_meta.db         # 메타DB (은행 마스터, 코드)
└── scripts/

3_Resources/R-DB/outputs/
└── fsc.db                   # 데이터DB (재무/경영/영업)
```

### 메타DB 스키마
```sql
-- 은행 마스터
CREATE TABLE banks (
    bank_cd TEXT UNIQUE,
    bank_nm TEXT NOT NULL,
    bank_type TEXT,
    group_nm TEXT
);

-- 데이터 유형
CREATE TABLE data_types (
    code TEXT PRIMARY KEY,
    name TEXT,
    operation TEXT
);

-- 경영지표 코드
CREATE TABLE metric_codes (
    code TEXT PRIMARY KEY,
    name TEXT,
    unit TEXT
);
```

### 데이터DB 스키마
```sql
-- 경영지표
CREATE TABLE bank_metrics (
    bas_ym TEXT,
    bank_nm TEXT,
    roa REAL,
    roe REAL,
    nim REAL,
    bis_ratio REAL,
    npl_ratio REAL,
    ldr REAL,
    UNIQUE(bas_ym, bank_nm)
);

-- 재무현황
CREATE TABLE bank_finance (
    bas_ym TEXT,
    bank_nm TEXT,
    total_assets REAL,
    total_liab REAL,
    total_equity REAL,
    UNIQUE(bas_ym, bank_nm)
);
```

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-fsc >> scripts >> fsc_api.py`
- 메타DB: `.claude >> skills >> api-fsc >> data >> fsc_meta.db`
- 데이터DB: `3_Resources >> R-DB >> outputs >> fsc.db`

## Limitations

- 일일 API 호출 제한: 1,000건 (개발계정)
- 페이지당 최대 조회: 100건
- 데이터 제공 범위: 최근 5년

## See Also

- [공공데이터포털 API](https://www.data.go.kr/)
- `api-fisis` 스킬: 금융감독원 금융통계
- `api-ecos` 스킬: 한국은행 경제통계
- `api-dart` 스킬: 전자공시시스템
