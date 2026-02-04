# -*- coding: utf-8 -*-
---
name: api-fisis
description: 금융감독원 금융통계정보시스템(FISIS) OpenAPI를 통해 국내 금융회사의 재무현황, 경영지표, 영업활동 정보를 조회하는 스킬. 은행, 보험, 증권 등 금융권역별 통계 데이터를 API로 수집하여 분석에 활용.
version: 2.0.0
---

# FISIS OpenAPI Skill

## Purpose

금융감독원 금융통계정보시스템(FISIS) OpenAPI를 통해 국내 금융회사의 각종 통계 데이터를 조회합니다.

**핵심 기능:**
1. 금융회사 일반현황 조회 (설립연도, 본점소재지, 점포현황)
2. 재무현황 조회 (자산, 부채, 자본)
3. 경영지표 조회 (ROA, ROE, BIS비율, NIM)
4. 영업활동 조회 (대출금, 예수금, 외화예금)
5. 금융권역별 통계표 조회

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 금융회사 재무 데이터를 API로 수집해야 할 때
- 은행별 경영지표를 비교 분석해야 할 때
- 금융통계 시계열 데이터가 필요할 때
- 금융권역별 현황을 파악해야 할 때

트리거 예시:
- "KB금융 경영지표 조회해줘"
- "국내 은행 ROE 비교해줘"
- "2024년 은행 재무현황 가져와줘"
- "IBK기업은행 최근 5년 실적 조회"

## API 개요

### Base URL
```
http://fisis.fss.or.kr/openapi/
```

### 인증
- API Key 방식 (쿼리 파라미터: `auth`)
- 인증키는 FISIS 사이트에서 신청
- 환경변수: `FISIS_API_KEY`

### 주요 API 엔드포인트

| API | 설명 | 엔드포인트 |
|-----|------|-----------|
| 통계표 목록 | 금융권역별 통계표 조회 | `/statisticsListSearch.json` |
| 통계 데이터 | 통계표 상세 데이터 조회 | `/statisticsInfoSearch.json` |
| 금융회사 목록 | 금융회사 리스트 조회 | `/companySearch.json` |
| 금융회사 상세 | 금융회사 상세 정보 | `/companyInfoSearch.json` |

### statisticsInfoSearch 파라미터 (v2.0 핵심)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `auth` | Y | API 인증키 |
| `listNo` | Y | 통계표 코드 (예: SA003) |
| `term` | Y | **기간 유형** (Q=분기, Y=연간) |
| `startBaseMm` | Y | 시작 기준월 (YYYYMM) |
| `endBaseMm` | Y | 종료 기준월 (YYYYMM) |
| `financeCd` | 통계표별 상이 | 금융회사 코드 |

**중요:** `term`은 기간값(202312)이 아니라 **기간 유형**(Q 또는 Y)입니다!

## Installation

### 필수 의존성
```bash
pip install requests python-dotenv
```

### 환경변수 설정
`.claude/.env` 파일에 API 키 추가:
```env
FISIS_API_KEY=your_api_key_here
```

## Workflow

### Step 1: 인증키 확인
```python
import os
from dotenv import load_dotenv

load_dotenv(".claude/.env")
api_key = os.getenv("FISIS_API_KEY")

if not api_key:
    print("FISIS_API_KEY가 설정되지 않았습니다.")
```

### Step 2: API 호출
```bash
# API 상태 확인
python .claude/skills/api-fisis/scripts/fisis_api.py --status

# 금융회사 목록 조회
python .claude/skills/api-fisis/scripts/fisis_api.py --list-companies --sector bank

# 특정 회사 경영지표 조회 (분기)
python .claude/skills/api-fisis/scripts/fisis_api.py --company "신한은행" --metrics --year 2024 --quarter 1

# 통계표 데이터 조회 (분기)
python .claude/skills/api-fisis/scripts/fisis_api.py --stat-code SA003 --year 2024 --quarter 1 --company "신한은행"
```

### Step 3: 결과 저장
```bash
# JSON 파일로 저장
python .claude/skills/api-fisis/scripts/fisis_api.py --company "신한은행" --metrics --year 2024 -q 1 --output result.json

# CSV 파일로 저장
python .claude/skills/api-fisis/scripts/fisis_api.py --stat-code SA003 --year 2024 -q 1 --company "신한은행" --output result.csv
```

## Scripts Reference

### `scripts/fisis_api.py`

**Purpose:** FISIS OpenAPI 호출 및 데이터 처리 (v2.0)

**Usage:**
```bash
# API 상태 확인
python fisis_api.py --status

# 금융권역 목록
python fisis_api.py --sectors

# 금융회사 목록
python fisis_api.py --list-companies --sector <권역코드>

# 통계표 목록
python fisis_api.py --list-stats --sector <권역코드>

# 통계 데이터 조회 (분기)
python fisis_api.py --stat-code <통계코드> --year <연도> --quarter <분기> --company <회사명>

# 경영지표 조회
python fisis_api.py --company <회사명> --metrics --year <연도> --quarter <분기>

# 재무요약 조회
python fisis_api.py --company <회사명> --financials --year <연도> --quarter <분기>
```

**Options:**

| 옵션 | 설명 |
|------|------|
| `--status` | API 엔드포인트 상태 확인 |
| `--sectors` | 금융권역 목록 출력 |
| `--sector CODE` | 금융권역 코드 (bank, insurance, securities 등) |
| `--list-companies` | 금융회사 목록 조회 |
| `--list-stats` | 통계표 목록 조회 |
| `--stat-code CODE` | 통계표 코드 |
| `--company NAME` | 금융회사명 |
| `--info` | 회사 기본정보 |
| `--metrics` | 경영지표 조회 |
| `--financials` | 재무요약 조회 |
| `--year YYYY` | 조회 연도 |
| `--quarter Q` | 분기 (1,2,3,4) |
| `--output FILE` | 결과 저장 파일 (json/csv) |

## 금융권역 코드

| 코드 | partDiv | 권역 | 설명 |
|------|---------|------|------|
| `bank` | A | 국내은행 | 시중/지방/특수은행 |
| `bank_foreign` | J | 외은지점 | 외국은행 국내지점 |
| `insurance_life` | H | 생명보험 | 생명보험사 |
| `insurance_nonlife` | I | 손해보험 | 손해보험사 |
| `securities` | F | 증권사 | 증권회사 |
| `asset_mgmt` | G | 자산운용 | 자산운용사 |
| `savings` | E | 저축은행 | 저축은행 |
| `card` | C | 신용카드 | 신용카드사 |
| `holding` | L | 금융지주 | 금융지주회사 |

## 주요 통계표 코드 (은행)

| 코드 | 통계표명 | 설명 |
|------|----------|------|
| `SA003` | 요약재무상태표(자산) | 자산 항목별 금액/비율 |
| `SA004` | 요약재무상태표(부채/자본) | 부채/자본 항목 |
| `SA017` | 수익성지표 | ROA, ROE, NIM 등 |
| `SA021` | 주요계정 및 지표 | 종합 경영지표 |
| `SA101` | 임직원현황 | 임직원 수 |
| `SA002` | 영업점포현황 | 점포 수 |

## Examples

### Example 1: 경영지표 조회
```bash
python .claude/skills/api-fisis/scripts/fisis_api.py \
    --company "신한은행" --metrics --year 2024 --quarter 1
```

**출력:**
```
=== 신한은행 경영지표 (2024년 1분기) ===
지표명                                             값
----------------------------------------------------------
실질총자산(평잔)                                  468.4조
자기자본(평잔)                                    30.5조
세후당기손익                                       2.6조
총자산순이익률(ROA)                                0.55%
자기자본순이익률(ROE)                               8.50%
원화예대금리차                                     2.01%
명목순이자마진(NIM)                                1.63%
...
```

### Example 2: 재무상태표 조회
```bash
python .claude/skills/api-fisis/scripts/fisis_api.py \
    --stat-code SA003 --year 2024 --quarter 1 --company "신한은행"
```

**출력:**
```
=== 통계 데이터: SA003 (2024년 1분기) - 신한은행 ===
총 222건

계정명                                        금액          비율
-----------------------------------------------------------------
현금 및 예치금                             215,717억        4.61%
유가증권                                 1,425,890억       30.45%
대출채권                                 2,840,123억       60.68%
...
```

### Example 3: Python 직접 사용
```python
from scripts.fisis_api import FisisAPI

api = FisisAPI()

# 2024년 1분기 경영지표 조회
metrics = api.get_metrics("신한은행", year=2024, quarter=1)
for item in metrics.get('data', []):
    print(f"{item['account_nm']}: {item['a']}")

# 재무상태표 조회
financials = api.get_statistics_data(
    stat_code='SA003',
    year=2024,
    quarter=1,
    company_code='0011625'  # 신한은행
)
```

## Korean Encoding (한글 인코딩)

**중요:** 모든 파일 작업에 UTF-8 인코딩 사용

```python
# 파일 읽기/쓰기
with open(file, 'r', encoding='utf-8') as f:
    data = f.read()

# CSV 저장 (BOM 포함)
with open(file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
```

## Error Handling

| 오류 코드 | 원인 | 해결 |
|-----------|------|------|
| `000` | 정상 | - |
| `010` | 인증키 오류 | API 키 확인 |
| `011` | 일일 호출 초과 | 다음날 재시도 |
| `020` | 필수 파라미터 누락 | 파라미터 확인 |
| `030` | 데이터 없음 | 조회 조건 수정 |
| `100` | financeCd 누락 | 금융회사 코드 필수 |
| `101` | term의 부적절한 값 | term=Q 또는 Y 사용 |

## Metadata DB

회사 코드 및 통계표 정보를 SQLite DB로 캐싱하여 빠른 조회를 지원합니다.

### DB 위치
```
.claude/skills/api-fisis/data/fisis_meta.db
```

### 메타DB 명령어
```bash
# DB 초기화
python .claude/skills/api-fisis/scripts/fisis_meta_db.py --init

# 전체 권역 금융회사 동기화
python .claude/skills/api-fisis/scripts/fisis_meta_db.py --fetch-all-companies

# 회사 코드 조회
python .claude/skills/api-fisis/scripts/fisis_meta_db.py --get-code "신한은행"

# DB 통계
python .claude/skills/api-fisis/scripts/fisis_meta_db.py --stats
```

## Version History

### v2.0.0 (2025-12-22)
- **BREAKING CHANGE**: term 파라미터 규격 변경
  - 이전: `term=202312` (기간값)
  - 현재: `term=Q` + `startBaseMm=202301` + `endBaseMm=202303` (기간유형 + 범위)
- 기간 변환 헬퍼 함수 추가 (`quarter_to_dates`, `year_to_dates`)
- CLI 출력 개선 (금액 포맷팅, 비율 표시)
- API 상태 확인 기능 개선

### v1.3.0
- 메타데이터 DB 전체 권역 동기화
- API 상태 확인 기능 추가
- statisticsInfoSearch API 이슈 문서화

## See Also

- [FISIS 금융통계정보시스템](https://fisis.fss.or.kr/)
- [공공데이터포털 금융통계 API](https://www.data.go.kr/data/15061304/openapi.do)
- `api-dart` 스킬: DART 전자공시시스템
- `md2db` 스킬: 분석 결과 DB 저장
