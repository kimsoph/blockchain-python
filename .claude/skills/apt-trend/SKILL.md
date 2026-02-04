# -*- coding: utf-8 -*-
---
name: apt-trend
description: apt.db 데이터를 기반으로 아파트 시장 시계열 트렌드를 분석하는 스킬. 이동평균, 추세선, 변동성, 계절성, 변곡점 감지 등 시계열 분석 지표를 산출하여 마크다운 테이블로 출력.
version: 1.0.0
---

# 아파트 시계열 트렌드 분석 Skill

## Purpose

apt.db에 저장된 아파트 거래 데이터를 기반으로 시계열 트렌드를 분석합니다.

**핵심 기능:**
1. **이동평균**: 3개월/6개월/12개월 이동평균
2. **추세선**: 선형/다항식 회귀 추세
3. **변동성**: 표준편차, 변동계수
4. **계절성**: 월별 계절 패턴
5. **변곡점**: 추세 전환점 감지
6. **시계열 비교**: 기간별 비교 분석

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 아파트 가격 추세를 분석할 때
- 거래량 시계열 변화를 파악할 때
- 시장의 변곡점(상승→하락, 하락→상승)을 찾을 때
- 계절적 패턴(봄철 이사 시즌 등)을 분석할 때
- apt-price-collector-trade 에이전트에서 시계열 분석 시

트리거 예시:
- "강남구 아파트 가격 추이 분석해줘"
- "2024년 아파트 거래량 시계열 보여줘"
- "서울 아파트 시장 변곡점 찾아줘"
- "월별 계절성 패턴 분석해줘"

## Prerequisites

### 데이터베이스
- **apt.db**: `3_Resources/R-DB/apt.db`
  - `apt_trades` 테이블: 매매 거래 데이터
  - `sync_status` 테이블: 동기화 상태

### 의존성
```bash
pip install pandas numpy scipy
```

## Workflow

### Step 1: 이동평균 분석
```bash
# 3, 6, 12개월 이동평균
python .claude/skills/apt-trend/scripts/apt_trend.py --ma 3,6,12 --region 11680 --period 202401-202512

# 특정 이동평균만
python .claude/skills/apt-trend/scripts/apt_trend.py --ma 6 --region 11680 --period 202401-202512
```

### Step 2: 추세선 분석
```bash
# 선형 추세
python .claude/skills/apt-trend/scripts/apt_trend.py --trend linear --region 11680 --period 202401-202512

# 다항 추세 (2차)
python .claude/skills/apt-trend/scripts/apt_trend.py --trend poly2 --region 11680 --period 202401-202512
```

### Step 3: 변동성 분석
```bash
# 변동성 지표
python .claude/skills/apt-trend/scripts/apt_trend.py --volatility --region 11680 --period 202401-202512
```

### Step 4: 계절성 분석
```bash
# 월별 계절 패턴
python .claude/skills/apt-trend/scripts/apt_trend.py --seasonality --region 11680 --period 202301-202512
```

### Step 5: 변곡점 감지
```bash
# 추세 전환점
python .claude/skills/apt-trend/scripts/apt_trend.py --turning-points --region 11680 --period 202401-202512
```

### Step 6: 종합 분석
```bash
# 모든 지표 종합
python .claude/skills/apt-trend/scripts/apt_trend.py --full --region 11680 --period 202401-202512
```

## Scripts Reference

### `scripts/apt_trend.py`

**Purpose:** 시계열 트렌드 분석 CLI

**Usage:**
```bash
python apt_trend.py <command> [options]
```

**Commands:**

| 옵션 | 설명 |
|------|------|
| `--ma N[,N,N]` | 이동평균 (개월) |
| `--trend TYPE` | 추세선 (linear/poly2/poly3) |
| `--volatility` | 변동성 분석 |
| `--seasonality` | 계절성 분석 |
| `--turning-points` | 변곡점 감지 |
| `--full` | 종합 분석 |

**Options:**

| 옵션 | 설명 |
|------|------|
| `--region CODE` | 지역코드 |
| `--period YYYYMM-YYYYMM` | 분석 기간 |
| `--metric TYPE` | 분석 대상 (price/volume) |
| `--output FILE` | 결과 저장 (md/json) |

## Analysis Metrics

### 1. 이동평균 (Moving Average)

| 유형 | 설명 |
|------|------|
| MA3 | 3개월 이동평균 (단기 추세) |
| MA6 | 6개월 이동평균 (중기 추세) |
| MA12 | 12개월 이동평균 (장기 추세) |

**골든크로스/데드크로스:**
- 골든크로스: 단기 MA가 장기 MA를 상향 돌파 (상승 신호)
- 데드크로스: 단기 MA가 장기 MA를 하향 돌파 (하락 신호)

### 2. 추세선 (Trend Line)

| 유형 | 수식 |
|------|------|
| 선형 | y = ax + b |
| 2차 다항 | y = ax² + bx + c |
| 3차 다항 | y = ax³ + bx² + cx + d |

**추세 방향:**
- 기울기 > 0: 상승 추세
- 기울기 < 0: 하락 추세
- 기울기 ≈ 0: 횡보

### 3. 변동성 (Volatility)

| 지표 | 설명 |
|------|------|
| 표준편차 (σ) | 가격 변동 폭 |
| 변동계수 (CV) | σ / 평균 x 100 (상대적 변동성) |
| 범위 (Range) | 최고가 - 최저가 |

**해석:**
- CV < 5%: 안정
- 5~10%: 보통
- 10~20%: 변동성 높음
- 20% 이상: 매우 불안정

### 4. 계절성 (Seasonality)

월별 거래량/가격 패턴 분석:
- 봄 (3~5월): 이사 성수기
- 여름 (6~8월): 비수기
- 가을 (9~11월): 이사 성수기
- 겨울 (12~2월): 비수기

### 5. 변곡점 (Turning Points)

| 유형 | 조건 |
|------|------|
| 저점 전환 | 하락 → 상승 |
| 고점 전환 | 상승 → 하락 |

**감지 방법:**
- 이동평균 교차
- 2차 미분 부호 변화
- 가격 모멘텀 반전

## Output Format

### 마크다운 테이블 (기본)

```markdown
## 시계열 추세 분석 (강남구, 2024.01~2025.12)

### 이동평균

| 년월 | 평균가 | MA3 | MA6 | MA12 | 신호 |
|------|--------|-----|-----|------|------|
| 2025.12 | 234,500 | 230,100 | 225,800 | 218,500 | 상승 |
| 2025.11 | 228,300 | 227,500 | 223,100 | 216,200 | 상승 |
| ... | ... | ... | ... | ... | ... |

### 추세 분석

| 지표 | 값 |
|------|-----|
| 추세 방향 | 상승 |
| 월평균 상승률 | +0.8% |
| R² | 0.87 |

### 변곡점

| 시점 | 유형 | 가격 | 비고 |
|------|------|------|------|
| 2024.06 | 저점 | 198,500 | 하락→상승 전환 |
| 2025.03 | 고점 | 245,000 | 상승→조정 전환 |
```

## Data Directory

### 파일 구조
```
.claude/skills/apt-trend/
├── SKILL.md
└── scripts/
    └── apt_trend.py
```

### 데이터 소스
```
3_Resources/R-DB/apt.db          ← 분석 대상 DB
    ├── apt_trades               ← 매매 거래 데이터
    └── sync_status              ← 동기화 상태
```

## Korean Encoding (한글 인코딩)

**중요:** 모든 출력에 UTF-8 인코딩 사용

## Error Handling

| 에러 상황 | 대응 |
|-----------|------|
| apt.db 없음 | 에러 메시지 출력, 종료 |
| 데이터 부족 | 최소 3개월 데이터 필요 안내 |
| 기간 외 데이터 | 가용 기간으로 자동 조정 |

## See Also

- `api-apt` 스킬: 데이터 동기화
- `apt-analytics` 스킬: 고급 분석 지표
- `apt-region` 스킬: 지역 비교 분석
- `apt-price-collector-trade` 에이전트: 실거래가 데이터 수집
