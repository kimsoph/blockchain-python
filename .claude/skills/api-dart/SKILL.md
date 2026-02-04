# -*- coding: utf-8 -*-
---
name: api-dart
description: 금융감독원 전자공시시스템(DART) OpenAPI를 통해 상장/비상장 기업의 공시정보, 기업개황, 재무제표를 조회하는 스킬. 사업보고서, 분기보고서 등 공시 원문 및 재무데이터 수집에 활용.
version: 1.2.0
---

# DART OpenAPI Skill

## Purpose

금융감독원 전자공시시스템(DART) OpenAPI를 통해 기업의 공시정보와 재무데이터를 조회합니다.

**핵심 기능:**
1. 공시검색: 기업별/기간별 공시보고서 검색
2. 기업개황: 기업 기본정보 조회 (대표자, 주소, 업종 등)
3. 재무제표: 전체 재무제표 및 주요계정 조회
4. 고유번호: 기업 고유번호 SQLite DB 관리 (114,000+ 기업)
5. **배당금 조회**: 연도별 배당금 지급 내역 조회 (v1.2.0 추가)

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 특정 기업의 공시 보고서를 검색할 때
- 기업의 기본정보(설립일, 대표자, 업종 등)가 필요할 때
- 재무제표 데이터(자산, 부채, 매출 등)를 조회할 때
- 여러 기업의 재무정보를 비교 분석할 때

트리거 예시:
- "삼성전자 최근 공시 보여줘"
- "네이버 기업개황 조회해줘"
- "SK하이닉스 2023년 재무제표 가져와줘"
- "카카오 분기보고서 검색"
- "기업은행 최근 5년 배당금 추이 조회해줘"

## API 개요

### Base URL
```
https://opendart.fss.or.kr/api/
```

### 인증
- API Key 방식 (쿼리 파라미터: `crtfc_key`)
- 인증키는 [OpenDART](https://opendart.fss.or.kr)에서 신청
- 환경변수: `DART_API_KEY`

### 주요 API 엔드포인트

| API | 설명 | 엔드포인트 |
|-----|------|-----------|
| 공시검색 | 공시보고서 검색 | `/list.json` |
| 기업개황 | 기업 기본정보 | `/company.json` |
| 고유번호 | 기업 고유번호 파일 | `/corpCode.xml` |
| 단일회사 주요계정 | 주요 재무계정 | `/fnlttSinglAcnt.json` |
| 단일회사 전체 재무제표 | 전체 계정과목 | `/fnlttSinglAcntAll.json` |
| 다중회사 주요계정 | 복수 기업 비교 | `/fnlttMultiAcnt.json` |

### 공통 파라미터

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `crtfc_key` | Y | API 인증키 (40자) |
| `corp_code` | API별 상이 | 고유번호 (8자) |

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
DART_API_KEY=your_api_key_here
```

## Workflow

### Step 1: 고유번호 DB 동기화
```bash
# 고유번호 다운로드 및 SQLite DB 저장 (최초 1회)
python .claude/skills/api-dart/scripts/dart_api.py --sync

# 강제 재동기화
python .claude/skills/api-dart/scripts/dart_api.py --sync --force

# DB 통계 확인
python .claude/skills/api-dart/scripts/dart_api.py --stats
```

### Step 2: 기업 검색
```bash
# 기업명으로 검색
python .claude/skills/api-dart/scripts/dart_api.py --search "삼성"

# 상장사만 검색
python .claude/skills/api-dart/scripts/dart_api.py --search "삼성" --listed-only
```

### Step 3: 데이터 조회
```bash
# 기업개황
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --info

# 공시검색
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --disclosure --start-date 20240101

# 재무제표
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --financials --year 2023
```

### Step 4: 결과 저장
```bash
# JSON 파일로 저장
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --financials --output result.json

# CSV 파일로 저장
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --financials --output result.csv
```

## Scripts Reference

### `scripts/dart_api.py`

**Purpose:** DART OpenAPI 호출 및 데이터 처리

**Usage:**
```bash
# 고유번호 DB 동기화
python dart_api.py --sync [--force]

# DB 통계 확인
python dart_api.py --stats

# 기업 검색
python dart_api.py --search <키워드> [--listed-only]

# 기업개황
python dart_api.py --company <회사명> --info

# 공시검색
python dart_api.py --company <회사명> --disclosure [--start-date YYYYMMDD] [--end-date YYYYMMDD]

# 재무제표 (전체)
python dart_api.py --company <회사명> --financials --year <연도> [--report annual|1Q|2Q|3Q]

# 재무제표 (주요계정)
python dart_api.py --company <회사명> --financials --summary --year <연도>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--sync` | 고유번호 다운로드 및 DB 동기화 |
| `--force` | 강제 동기화 (--sync와 함께 사용) |
| `--stats` | DB 통계 출력 |
| `--search KEYWORD` | 기업명 검색 |
| `--listed-only` | 상장사만 검색 |
| `--company NAME` | 회사명 지정 |
| `--info` | 기업개황 조회 |
| `--disclosure` | 공시 검색 |
| `--financials` | 재무제표 조회 |
| `--summary` | 주요계정만 조회 |
| `--year YYYY` | 사업연도 (기본: 전년도) |
| `--report TYPE` | 보고서 유형 (annual/1Q/2Q/3Q) |
| `--fs-div DIV` | 재무제표 구분 (OFS/CFS) |
| `--start-date YYYYMMDD` | 공시 검색 시작일 |
| `--end-date YYYYMMDD` | 공시 검색 종료일 |
| `--disclosure-type A~J` | 공시유형 |
| `--corp-cls Y/K/N/E` | 법인구분 |
| `--limit N` | 조회 건수 |
| `--output FILE` | 결과 저장 파일 (json/csv) |

### `scripts/dart_meta_db.py`

**Purpose:** 고유번호 SQLite DB 관리

**Usage:**
```bash
# DB 초기화
python dart_meta_db.py --init

# 고유번호 동기화
python dart_meta_db.py --sync [--force]

# 기업 검색
python dart_meta_db.py --search <키워드> [--listed-only]

# 회사 코드 조회
python dart_meta_db.py --get-code <회사명>

# 기업 정보 조회
python dart_meta_db.py --info <고유번호>

# DB 통계
python dart_meta_db.py --stats
```

## 코드 참조

### 보고서 코드

| 코드 | 옵션 | 설명 |
|------|------|------|
| `11011` | annual | 사업보고서 |
| `11012` | 2Q | 반기보고서 |
| `11013` | 1Q | 1분기보고서 |
| `11014` | 3Q | 3분기보고서 |

### 공시유형 코드

| 코드 | 설명 |
|------|------|
| A | 정기공시 |
| B | 주요사항보고 |
| C | 발행공시 |
| D | 지분공시 |
| E | 기타공시 |
| F | 외부감사관련 |
| G | 펀드공시 |
| H | 자산유동화 |
| I | 거래소공시 |
| J | 공정위공시 |

### 법인구분 코드

| 코드 | 설명 |
|------|------|
| Y | 유가증권시장 |
| K | 코스닥 |
| N | 코넥스 |
| E | 기타 |

### 재무제표 구분

| 코드 | 설명 |
|------|------|
| OFS | 재무제표 (개별) |
| CFS | 연결재무제표 |

### 재무제표 종류

| 코드 | 설명 |
|------|------|
| BS | 재무상태표 |
| IS | 손익계산서 |
| CIS | 포괄손익계산서 |
| CF | 현금흐름표 |
| SCE | 자본변동표 |

## Examples

### Example 1: 기업 검색 및 개황 조회
```bash
# 삼성 관련 기업 검색
python .claude/skills/api-dart/scripts/dart_api.py --search "삼성"

# 삼성전자 기업개황
python .claude/skills/api-dart/scripts/dart_api.py --company "삼성전자" --info
```

**출력:**
```
=== 삼성전자 기업개황 ===
  정식명칭: 삼성전자주식회사
  영문명칭: SAMSUNG ELECTRONICS CO.,LTD
  대표자: 한종희, 경계현
  법인구분: 유가증권시장
  주소: 경기도 수원시 영통구 삼성로 129
  홈페이지: www.samsung.com
  업종코드: 264
  설립일: 19690113
  결산월: 12
```

### Example 2: 공시 검색
```bash
python .claude/skills/api-dart/scripts/dart_api.py \
    --company "삼성전자" --disclosure \
    --start-date 20240101 --end-date 20240630 \
    --disclosure-type A
```

**출력:**
```
=== 공시 검색 결과 (15건) ===
접수일       회사명              보고서명
---------------------------------------------------------------------------
20240515    삼성전자            분기보고서 (2024.03)
20240410    삼성전자            사업보고서 (2023.12)
...
```

### Example 3: 재무제표 조회
```bash
# 연결재무제표 전체
python .claude/skills/api-dart/scripts/dart_api.py \
    --company "삼성전자" --financials --year 2023 --fs-div CFS

# 주요계정만
python .claude/skills/api-dart/scripts/dart_api.py \
    --company "삼성전자" --financials --summary --year 2023
```

**출력:**
```
=== 삼성전자 2023년 전체 재무제표 (연결재무제표) ===

[재무상태표]
계정명                              당기금액             전기금액
------------------------------------------------------------------------
자산총계                      455,905,294,000,000  426,614,174,000,000
부채총계                       92,228,813,000,000   90,572,400,000,000
자본총계                      363,676,481,000,000  336,041,774,000,000
...
```

### Example 4: Python 직접 사용
```python
from scripts.dart_api import DartAPI

api = DartAPI()

# 기업개황 조회
info = api.get_company_info(corp_name="삼성전자")
print(f"대표자: {info.get('ceo_nm')}")

# 재무제표 조회
fs = api.get_financial_summary(corp_name="삼성전자", bsns_year=2023)
for item in fs.get('list', []):
    print(f"{item['account_nm']}: {item['thstrm_amount']}")
```

### Example 5: 배당금 추이 조회 (v1.2.0)
```python
from scripts.dart_api import DartAPI

api = DartAPI()

# 최근 5년 배당금 추이 조회
dividend_data = api.get_dividend_history("기업은행", start_year=2019, end_year=2024)

for year in sorted(dividend_data.keys(), reverse=True):
    amount_억 = dividend_data[year] / 100000000
    print(f"{year}년: {amount_억:,.0f}억원")
```

**출력:**
```
=== IBK기업은행 배당금 추이 ===
2024년: 7,847억원
2023년: 7,655억원
2022년: 6,220억원
2021년: 3,729억원
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
| `000` | 정상 | - |
| `010` | 등록되지 않은 인증키 | API 키 확인 |
| `011` | 사용할 수 없는 인증키 | API 키 상태 확인 |
| `012` | 허용되지 않은 IP | IP 등록 확인 |
| `013` | 조회된 데이터 없음 | 조회 조건 수정 |
| `020` | 요청 제한 초과 | 요청 건수 조절 |
| `100` | 필드 누락 | 필수 파라미터 확인 |
| `800` | 시스템 점검 | 잠시 후 재시도 |
| `900` | 정의되지 않은 오류 | 로그 확인 |

## Data Directory

### 데이터 파일 위치
```
.claude/skills/api-dart/data/
├── dart_meta.db         # 고유번호 SQLite DB
└── (output files)       # 조회 결과 저장
```

### 메타데이터 DB 스키마
```sql
-- 기업 고유번호
CREATE TABLE corporations (
    id INTEGER PRIMARY KEY,
    corp_code TEXT UNIQUE,    -- 고유번호 (8자리)
    corp_name TEXT,           -- 회사명
    corp_name_eng TEXT,       -- 영문명
    stock_code TEXT,          -- 종목코드 (상장사만)
    modify_date TEXT,         -- 최종변경일
    is_listed INTEGER,        -- 상장 여부
    updated_at TEXT
);
```

### 고유번호 DB 관리
- 최초 실행 시 자동 다운로드 및 DB 저장
- 1일 이내 재동기화 스킵
- `--sync --force`로 강제 갱신
- FTS5 전문 검색 지원

### DB 통계 (v1.1.0 기준)
- 전체 기업: 114,835개
- 상장사: 3,935개
- 비상장: 110,900개

## Path Convention

경로 표시 시 `>>` 사용:
- 스크립트: `.claude >> skills >> api-dart >> scripts >> dart_api.py`
- 데이터: `.claude >> skills >> api-dart >> data >> dart_meta.db`

## Limitations

- 일일 API 호출 제한: 10,000건
- 페이지당 최대 조회: 100건
- 재무제표: 2015년 이후 데이터만 제공
- 고유번호 DB: 114,000+ 기업 (상장+비상장)

## Version History

### v1.2.0 (2025-12-23)
- **NEW**: `get_dividend_history()` 메서드 추가
  - 연도별 배당금 지급 내역 일괄 조회
  - 당기/전기/전전기 데이터 자동 수집
- **NEW**: `get_financial_all()` 별칭 메서드 추가
  - `get_financial_statements()`의 하위 호환성 별칭

### v1.1.0
- SQLite 메타데이터 DB 지원
- XML 파싱 대신 DB 조회로 성능 향상
- FTS5 전문 검색 지원

### v1.0.0
- 최초 릴리스
- 공시검색, 기업개황, 재무제표 조회 기능

## See Also

- [OpenDART](https://opendart.fss.or.kr/) - 전자공시시스템
- [OpenDART 개발가이드](https://opendart.fss.or.kr/guide/main.do)
- `api-fisis` 스킬: FISIS 금융통계정보시스템
- `md2db` 스킬: 분석 결과 DB 저장
