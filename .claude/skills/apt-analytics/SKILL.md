# -*- coding: utf-8 -*-
---
name: apt-analytics
description: apt.db 데이터를 기반으로 아파트 시장 고급 분석 지표를 산출하는 스킬. 전세가율, 가격변동률, 평단가, 거래회전율, 면적대별/가격대별 통계, 시장과열지수 등 다양한 분석 지표를 계산하여 마크다운 테이블로 출력.
version: 1.0.0
---

# 아파트 고급 분석 지표 Skill

## Purpose

apt.db에 저장된 아파트 매매/전월세 거래 데이터를 기반으로 고급 분석 지표를 산출합니다.

**핵심 기능:**
1. **전세가율**: 전세보증금 / 매매가 비율
2. **가격변동률**: MoM, QoQ, YoY 가격 변화율
3. **평단가**: 전용면적당 거래가
4. **거래회전율**: 거래건수 / 추정 세대수
5. **면적대별 통계**: 면적 구간별 건수, 평균가, 비중
6. **가격대별 분포**: 가격 구간별 건수, 비중
7. **시장과열지수**: 복합 지표 (거래량 + 가격상승률 + 전세가율)

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 특정 지역의 전세가율을 확인할 때
- 아파트 가격 변동률(전월/전분기/전년 대비)을 분석할 때
- 면적대별, 가격대별 거래 분포를 파악할 때
- 시장 과열 여부를 판단할 때
- apt-price-collector-trade 에이전트에서 분석 지표 산출 시

트리거 예시:
- "강남구 전세가율 분석해줘"
- "용산구 아파트 가격 변동률 확인해줘"
- "서울 면적대별 거래 현황"
- "2025년 하반기 시장과열지수 산출해줘"

## Prerequisites

### 데이터베이스
- **apt.db**: `3_Resources/R-DB/apt.db`
  - `apt_trades` 테이블: 매매 거래 데이터
  - `apt_rents` 테이블: 전월세 거래 데이터
  - `sync_status` 테이블: 동기화 상태

### 의존성
```bash
pip install pandas numpy
```

## Workflow

### Step 1: 전세가율 산출
```bash
# 특정 지역/년월 전세가율
python .claude/skills/apt-analytics/scripts/apt_analytics.py --jeonse-ratio --region 11680 --ym 202512

# 복수 지역 비교
python .claude/skills/apt-analytics/scripts/apt_analytics.py --jeonse-ratio --region 11680,41135,11170 --ym 202512
```

### Step 2: 가격변동률 산출
```bash
# 전월 대비 (MoM)
python .claude/skills/apt-analytics/scripts/apt_analytics.py --price-change --region 11680 --period mom

# 전년 동월 대비 (YoY)
python .claude/skills/apt-analytics/scripts/apt_analytics.py --price-change --region 11680 --period yoy

# 전분기 대비 (QoQ)
python .claude/skills/apt-analytics/scripts/apt_analytics.py --price-change --region 11680 --period qoq
```

### Step 3: 면적대별 통계
```bash
# 면적 구간별 거래 통계
python .claude/skills/apt-analytics/scripts/apt_analytics.py --by-area --region 11680 --ym 202512
```

### Step 4: 가격대별 분포
```bash
# 가격 구간별 거래 분포
python .claude/skills/apt-analytics/scripts/apt_analytics.py --by-price --region 11680 --ym 202512
```

### Step 5: 시장과열지수
```bash
# 시장과열지수 산출
python .claude/skills/apt-analytics/scripts/apt_analytics.py --overheat-index --region 11680 --ym 202512
```

### Step 6: 종합 분석
```bash
# 모든 지표 종합 분석
python .claude/skills/apt-analytics/scripts/apt_analytics.py --full --region 11680 --ym 202512

# 기간 범위 종합 분석
python .claude/skills/apt-analytics/scripts/apt_analytics.py --full --region 11680 --period 202507-202512
```

## Scripts Reference

### `scripts/apt_analytics.py`

**Purpose:** 고급 분석 지표 산출 CLI

**Usage:**
```bash
python apt_analytics.py <command> [options]
```

**Commands:**

| 옵션 | 설명 |
|------|------|
| `--jeonse-ratio` | 전세가율 산출 |
| `--price-change` | 가격변동률 산출 |
| `--by-area` | 면적대별 통계 |
| `--by-price` | 가격대별 분포 |
| `--overheat-index` | 시장과열지수 |
| `--full` | 종합 분석 (모든 지표) |

**Options:**

| 옵션 | 설명 |
|------|------|
| `--region CODE` | 지역코드 (쉼표 구분 복수 가능) |
| `--ym YYYYMM` | 분석 년월 |
| `--period YYYYMM-YYYYMM` | 분석 기간 (mom/qoq/yoy 또는 범위) |
| `--output FILE` | 결과 저장 (md/json) |

## Analysis Metrics

### 1. 전세가율 (Jeonse Ratio)

| 지표 | 산출 방법 |
|------|----------|
| 전세가율 | AVG(전세보증금) / AVG(매매가) x 100 |
| 면적별 전세가율 | 면적 구간별 전세가율 |

**해석:**
- 60% 이하: 매수 유리 (전세가율 낮음)
- 60~70%: 적정 수준
- 70~80%: 매도 유리 (전세가율 높음)
- 80% 이상: 과열 위험 (갭투자 주의)

### 2. 가격변동률 (Price Change)

| 지표 | 산출 방법 |
|------|----------|
| MoM | (현월 평균가 - 전월 평균가) / 전월 평균가 x 100 |
| QoQ | (현분기 평균가 - 전분기 평균가) / 전분기 평균가 x 100 |
| YoY | (현월 평균가 - 전년동월 평균가) / 전년동월 평균가 x 100 |

### 3. 평단가 (Price per Area)

| 지표 | 산출 방법 |
|------|----------|
| 평단가 (만원/㎡) | 거래가 / 전용면적 |
| 평균 평단가 | AVG(평단가) |
| 최고 평단가 | MAX(평단가) |

### 4. 면적대별 통계 (By Area)

| 면적 구간 | 범위 |
|-----------|------|
| 초소형 | ~40㎡ 미만 |
| 소형 | 40~60㎡ 미만 |
| 중소형 | 60~85㎡ 미만 |
| 중대형 | 85~135㎡ 미만 |
| 대형 | 135㎡ 이상 |

### 5. 가격대별 분포 (By Price)

| 가격 구간 | 범위 |
|-----------|------|
| ~3억 | 30,000만원 미만 |
| 3~6억 | 30,000~60,000만원 |
| 6~10억 | 60,000~100,000만원 |
| 10~20억 | 100,000~200,000만원 |
| 20~30억 | 200,000~300,000만원 |
| 30억~ | 300,000만원 이상 |

### 6. 시장과열지수 (Overheat Index)

복합 지표 (0~100점):
- 거래량 점수 (30점): 전년 동월 대비 거래량 증감
- 가격상승률 점수 (40점): 전년 동월 대비 가격 상승률
- 전세가율 점수 (30점): 전세가율 수준

**해석:**
- 0~30: 침체
- 30~50: 안정
- 50~70: 활황
- 70~100: 과열

## Output Format

### 마크다운 테이블 (기본)

```markdown
## 전세가율 분석 (강남구, 2025.12)

| 구분 | 매매 평균가 | 전세 평균가 | 전세가율 |
|------|------------|------------|----------|
| 전체 | 234,500만원 | 163,150만원 | 69.6% |
| 소형 (60㎡ 미만) | 125,000만원 | 97,500만원 | 78.0% |
| 중형 (60~85㎡) | 215,000만원 | 150,500만원 | 70.0% |
| 대형 (85㎡ 이상) | 385,000만원 | 250,000만원 | 64.9% |
```

## Data Directory

### 파일 구조
```
.claude/skills/apt-analytics/
├── SKILL.md
└── scripts/
    └── apt_analytics.py
```

### 데이터 소스
```
3_Resources/R-DB/apt.db          ← 분석 대상 DB
    ├── apt_trades               ← 매매 거래 데이터
    ├── apt_rents                ← 전월세 거래 데이터
    └── sync_status              ← 동기화 상태
```

## Korean Encoding (한글 인코딩)

**중요:** 모든 출력에 UTF-8 인코딩 사용

## Error Handling

| 에러 상황 | 대응 |
|-----------|------|
| apt.db 없음 | 에러 메시지 출력, 종료 |
| 지역 데이터 없음 | 해당 지역 동기화 필요 안내 |
| 기간 데이터 부족 | 비교 불가 명시, 가용 데이터만 분석 |

## See Also

- `api-apt` 스킬: 데이터 동기화
- `apt-trend` 스킬: 시계열 트렌드 분석
- `apt-region` 스킬: 지역 비교 분석
- `apt-price-collector-trade` 에이전트: 실거래가 데이터 수집
