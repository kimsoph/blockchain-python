# -*- coding: utf-8 -*-
---
name: api-yahoo
description: Yahoo Finance에서 글로벌/한국 주식의 주가(OHLCV), 재무제표, 배당 데이터를 조회하고 SQLite DB에 누적 저장하는 스킬
version: 2.0.0
---

# Yahoo Finance Skill

## Purpose

yfinance 라이브러리를 통해 주식 데이터를 조회하고 **SQLite DB에 누적 저장**합니다. **API 키 불필요.**

**핵심 기능:**
1. 주가 조회: OHLCV (시가/고가/저가/종가/거래량) 시계열 데이터
2. 재무제표: 손익계산서, 대차대조표, 현금흐름표
3. 배당 이력: 과거 배당금 지급 내역
4. 기업 정보: 기본 정보, 섹터, 시가총액 등
5. **DB 저장**: yahoo.db에 누적 저장 (시계열 분석 용이)
6. 메타DB: 종목 코드-이름 매핑 캐싱 (DART 연동)

## When to Use This Skill

트리거 예시:
- "삼성전자 최근 1년 주가 조회해줘"
- "코스피, 다우, 나스닥 지수 차트 그려줘"
- "애플 분기별 재무제표 가져와줘"
- "원/달러 환율 추이 보여줘"
- "AAPL 주가 데이터 DB에 저장해줘"

## Installation

```bash
pip install yfinance pandas
```

## 데이터 저장 위치

```
3_Resources/R-DB/yahoo.db
├── price_data        # 주가 데이터 (OHLCV)
├── financial_data    # 재무제표
├── dividend_data     # 배당 이력
└── collection_log    # 수집 로그
```

## Workflow

### Step 1: 데이터 조회 (자동 DB 저장)

```bash
# 주가 조회 (자동으로 DB에 저장됨)
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker AAPL --price --period 1y

# 한국 종목 주가
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker 005930 --price --period 6mo

# 지수 데이터
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker ^KS11 --price --period 1mo   # 코스피
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker ^DJI --price --period 1mo    # 다우
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker ^IXIC --price --period 1mo   # 나스닥

# 환율 데이터
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker USDKRW=X --price --period 1mo   # 원/달러
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker USDJPY=X --price --period 1mo   # 엔/달러

# 재무제표
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker AAPL --financials

# 배당 이력
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker AAPL --dividends

# DB 저장 없이 조회만 (필요한 경우)
python .claude/skills/api-yahoo/scripts/yahoo_api.py --ticker AAPL --price --period 1y --no-save-db
```

### Step 2: DB에서 데이터 조회

```bash
# 저장된 주가 데이터 조회
python .claude/skills/api-yahoo/scripts/yahoo_api.py --query-db price --ticker ^KS11 --limit 30

# 특정 기간 조회
python .claude/skills/api-yahoo/scripts/yahoo_api.py --query-db price --ticker AAPL --start-date 2026-01-01 --end-date 2026-01-31

# DB 통계 확인
python .claude/skills/api-yahoo/scripts/yahoo_api.py --data-db-stats
```

### Step 3: 차트 시각화

DB에서 데이터를 조회하여 make-chart 스킬로 시각화:

```python
import sqlite3
import pandas as pd

# DB 연결
conn = sqlite3.connect('3_Resources/R-DB/yahoo.db')

# 데이터 조회
df = pd.read_sql_query('''
    SELECT date, close FROM price_data
    WHERE ticker = '^KS11'
    ORDER BY date
''', conn)

# make-chart 스킬로 시각화
```

## 티커 형식

| 시장 | 형식 | 예시 |
|------|------|------|
| 미국 | 심볼 그대로 | AAPL, MSFT, GOOGL, TSLA |
| 코스피 | 종목코드.KS | 005930.KS (삼성전자) |
| 코스닥 | 종목코드.KQ | 035720.KQ (카카오) |

**자동 변환**: 6자리 숫자 입력 시 자동으로 시장 접미사 추가
- `005930` → `005930.KS` (메타DB에서 시장 조회)
- `삼성전자` → `005930.KS` (메타DB에서 종목 검색)

### 주요 지수

| 지수 | 티커 | 설명 |
|------|------|------|
| 코스피 | ^KS11 | KOSPI Composite Index |
| 코스닥 | ^KQ11 | KOSDAQ Composite Index |
| 다우존스 | ^DJI | Dow Jones Industrial Average |
| 나스닥 | ^IXIC | NASDAQ Composite |
| S&P 500 | ^GSPC | S&P 500 Index |
| 닛케이225 | ^N225 | Nikkei 225 |

### 환율

| 환율 | 티커 | 설명 |
|------|------|------|
| 원/달러 | USDKRW=X | USD to KRW |
| 엔/달러 | USDJPY=X | USD to JPY |
| 유로/달러 | EURUSD=X | EUR to USD |
| 위안/달러 | USDCNY=X | USD to CNY |

### 원자재 선물

| 자산 | 티커 | 설명 |
|------|------|------|
| 금 | GC=F | Gold Futures (COMEX) |
| 은 | SI=F | Silver Futures (COMEX) |
| 구리 | HG=F | Copper Futures (COMEX) |
| WTI 원유 | CL=F | Crude Oil WTI (NYMEX) |
| 브렌트 원유 | BZ=F | Crude Oil Brent (ICE) |
| 천연가스 | NG=F | Natural Gas (NYMEX) |

## CLI 옵션

### 조회

| 옵션 | 설명 |
|------|------|
| `--ticker, -t` | 티커 심볼 (필수) |
| `--price` | 주가 조회 (OHLCV) |
| `--financials` | 재무제표 조회 |
| `--dividends` | 배당 이력 조회 |
| `--info` | 기업 정보 조회 |

### 주가 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--period` | 조회 기간 | 1y |
| `--interval` | 데이터 간격 | 1d |
| `--start-date` | 시작일 (YYYY-MM-DD) | - |
| `--end-date` | 종료일 (YYYY-MM-DD) | - |

**period 값**: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
**interval 값**: 1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo

### DB 저장/조회

| 옵션 | 설명 |
|------|------|
| `--no-save-db` | DB 저장 안 함 (기본: 자동 저장) |
| `--query-db TYPE` | DB에서 조회 (price/financial/dividend) |
| `--data-db-stats` | DB 통계 출력 |

> **Note**: 데이터 조회 시 **자동으로 DB에 저장**됩니다. 저장하지 않으려면 `--no-save-db` 옵션을 사용하세요.

### 기타

| 옵션 | 설명 |
|------|------|
| `--sync-kr` | 한국 종목 DB 동기화 (DART 연동) |
| `--search KEYWORD` | 종목 검색 |
| `--market` | 시장 필터 (kospi/kosdaq/nasdaq/nyse) |
| `--quarterly, -q` | 분기별 재무제표 |
| `--limit` | 결과 행 수 (기본: 50) |

## Python API 사용

```python
from yahoo_api import YahooAPI

api = YahooAPI()

# 주가 조회
df = api.get_price_history("AAPL", period="1y")

# DB 저장 (권장)
api.save_price_to_db("AAPL", df)

# 재무제표 조회 + DB 저장
financials = api.get_all_financials("AAPL", quarterly=True)
api.save_financial_to_db("AAPL", "income", financials['income'], "quarterly")

# DB에서 조회
df = api.query_db("price", ticker="AAPL", start_date="2026-01-01", limit=100)

# DB 통계
stats = api.get_data_db_stats()
print(stats)
```

## DB 스키마

### price_data (주가)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| ticker | TEXT | 티커 심볼 |
| date | TEXT | 날짜 (YYYY-MM-DD) |
| open | REAL | 시가 |
| high | REAL | 고가 |
| low | REAL | 저가 |
| close | REAL | 종가 |
| volume | INTEGER | 거래량 |
| collected_at | TEXT | 수집 시각 |

### financial_data (재무제표)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| ticker | TEXT | 티커 심볼 |
| report_type | TEXT | 보고서 유형 (income/balance/cashflow) |
| fiscal_date | TEXT | 회계연도 |
| metric_name | TEXT | 지표명 |
| metric_value | REAL | 지표값 |
| period_type | TEXT | 기간 (annual/quarterly) |

### dividend_data (배당)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| ticker | TEXT | 티커 심볼 |
| date | TEXT | 배당일 |
| dividend | REAL | 배당금 |

## 주의사항

### yfinance 한계

| 항목 | 한계 | 대응 |
|------|------|------|
| 비공식 API | Yahoo 정책 변경 시 중단 가능 | 에러 처리 강화 |
| Rate Limit | 과다 요청 시 차단 | 요청 간 딜레이 |
| 한국 종목 | 재무제표 일부 누락 | DART 병행 사용 |
| 실시간 아님 | 15-20분 지연 | 실시간 필요시 다른 소스 |
| 분/시간 데이터 | 최근 60일만 조회 가능 | 장기 분석은 일별 사용 |

### 권장 사용 패턴

```markdown
## 글로벌 주식/지수 분석
1. api-yahoo 스킬로 데이터 조회 + DB 저장 (--save-db)
2. DB에서 시계열 데이터 조회
3. make-chart 스킬로 시각화

## 한국 주식 심층 분석
1. api-yahoo: 주가 이력, 기본 재무
2. api-dart: 공시 재무제표 (상세)
3. 두 소스 교차 검증 권장
```

## 파일 구조

```
.claude >> skills >> api-yahoo/
├── SKILL.md                    # 이 문서
├── data/
│   └── yahoo_meta.db           # 메타데이터 DB (종목 코드-이름 매핑)
└── scripts/
    ├── yahoo_api.py            # API 클라이언트
    └── yahoo_meta_db.py        # 메타DB 관리

3_Resources >> R-DB/
└── yahoo.db                    # 수집 데이터 DB (주가/재무/배당)
```

## 관련 스킬

- `api-dart`: 한국 기업 공시 재무제표 (상세)
- `make-chart`: 주가 데이터 차트 시각화
- `api-fisis`: 금융회사 경영지표
- `api-ecos`: 한국은행 경제통계
