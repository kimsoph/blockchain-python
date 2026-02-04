# -*- coding: utf-8 -*-
---
name: apt-region
description: apt.db 데이터를 기반으로 아파트 지역별 비교 분석을 수행하는 스킬. 지역 랭킹, 지역 간 비교, 인접 지역 비교, 시도별 집계, 가격 격차 분석 등을 마크다운 테이블로 출력.
version: 1.0.0
---

# 아파트 지역 비교 분석 Skill

## Purpose

apt.db에 저장된 아파트 거래 데이터를 기반으로 지역별 비교 분석을 수행합니다.

**핵심 기능:**
1. **지역 랭킹**: 평균가/거래량 기준 TOP N 지역
2. **지역 비교**: 복수 지역 직접 비교
3. **인접 지역**: 같은 시도 내 지역 비교
4. **시도 집계**: 시도별 평균 통계
5. **가격 격차**: 지역 간 가격 차이 분석

## When to Use This Skill

다음 상황에서 이 스킬을 사용:
- 전국 아파트 가격 순위를 파악할 때
- 특정 지역과 다른 지역을 비교할 때
- 서울/경기 등 시도별 통계가 필요할 때
- apt-price-collector-trade 에이전트에서 지역 비교 시

트리거 예시:
- "전국 아파트 가격 TOP 20 지역 보여줘"
- "강남구와 분당구 아파트 가격 비교해줘"
- "서울 구별 가격 순위 알려줘"
- "시도별 아파트 평균가 비교"

## Prerequisites

### 데이터베이스
- **apt.db**: `3_Resources/R-DB/apt.db`
  - `apt_trades` 테이블: 매매 거래 데이터
  - `sync_status` 테이블: 동기화 상태
- **apt_meta.db**: `.claude/skills/api-apt/data/apt_meta.db`
  - `region_codes` 테이블: 지역코드 마스터

### 의존성
```bash
pip install pandas
```

## Workflow

### Step 1: 지역 랭킹 조회
```bash
# 전국 가격 TOP 20
python .claude/skills/apt-region/scripts/apt_region.py --rank top20 --ym 202512

# 거래량 TOP 20
python .claude/skills/apt-region/scripts/apt_region.py --rank top20 --ym 202512 --by volume

# TOP 10/30
python .claude/skills/apt-region/scripts/apt_region.py --rank top10 --ym 202512
python .claude/skills/apt-region/scripts/apt_region.py --rank top30 --ym 202512
```

### Step 2: 지역 비교
```bash
# 두 지역 비교
python .claude/skills/apt-region/scripts/apt_region.py --compare 11680,41135 --ym 202512

# 복수 지역 비교
python .claude/skills/apt-region/scripts/apt_region.py --compare 11680,41135,11170,11650 --ym 202512
```

### Step 3: 인접 지역 비교
```bash
# 서울 내 구별 비교 (11680=강남구 기준)
python .claude/skills/apt-region/scripts/apt_region.py --adjacent 11680 --ym 202512

# 특정 지역 기준 같은 시도 내 비교
python .claude/skills/apt-region/scripts/apt_region.py --adjacent 41135 --ym 202512
```

### Step 4: 시도별 집계
```bash
# 시도별 평균 통계
python .claude/skills/apt-region/scripts/apt_region.py --by-sido --ym 202512
```

### Step 5: 가격 격차 분석
```bash
# 두 지역 간 가격 격차
python .claude/skills/apt-region/scripts/apt_region.py --gap 11680,41135 --ym 202512
```

### Step 6: 종합 분석
```bash
# 종합 분석 (랭킹 + 시도별)
python .claude/skills/apt-region/scripts/apt_region.py --full --ym 202512
```

## Scripts Reference

### `scripts/apt_region.py`

**Purpose:** 지역 비교 분석 CLI

**Usage:**
```bash
python apt_region.py <command> [options]
```

**Commands:**

| 옵션 | 설명 |
|------|------|
| `--rank TOPN` | 지역 랭킹 (top10/top20/top30) |
| `--compare CODES` | 지역 비교 (쉼표 구분) |
| `--adjacent CODE` | 인접 지역 비교 |
| `--by-sido` | 시도별 집계 |
| `--gap CODES` | 가격 격차 분석 |
| `--full` | 종합 분석 |

**Options:**

| 옵션 | 설명 |
|------|------|
| `--ym YYYYMM` | 분석 년월 |
| `--by TYPE` | 정렬 기준 (price/volume) |
| `--output FILE` | 결과 저장 (md/json) |

## Analysis Outputs

### 1. 지역 랭킹 (Region Ranking)

| 순위 | 지역 | 시도 | 평균가 | 거래량 | 평단가 |
|------|------|------|--------|--------|--------|
| 1 | 강남구 | 서울 | 245,000만원 | 523건 | 4,250만/㎡ |
| 2 | 서초구 | 서울 | 228,000만원 | 412건 | 3,980만/㎡ |
| ... | ... | ... | ... | ... | ... |

### 2. 지역 비교 (Region Compare)

| 지역 | 시도 | 평균가 | 거래량 | 전세가율 | 변동률(YoY) |
|------|------|--------|--------|----------|-------------|
| 강남구 | 서울 | 245,000 | 523 | 62.5% | +8.2% |
| 분당구 | 성남 | 158,000 | 382 | 68.3% | +5.7% |

### 3. 가격 격차 (Price Gap)

| 비교 | 지역A | 지역B | 가격차 | 격차율 |
|------|-------|-------|--------|--------|
| 강남 vs 분당 | 245,000 | 158,000 | 87,000 | 55.1% |

## Data Directory

### 파일 구조
```
.claude/skills/apt-region/
├── SKILL.md
└── scripts/
    └── apt_region.py
```

### 데이터 소스
```
3_Resources/R-DB/apt.db                      ← 거래 데이터
.claude/skills/api-apt/data/apt_meta.db      ← 지역코드 마스터
```

## Korean Encoding (한글 인코딩)

**중요:** 모든 출력에 UTF-8 인코딩 사용

## Error Handling

| 에러 상황 | 대응 |
|-----------|------|
| apt.db 없음 | 에러 메시지 출력, 종료 |
| 지역코드 없음 | 지역코드 목록 안내 |
| 데이터 없음 | 동기화 필요 안내 |

## See Also

- `api-apt` 스킬: 데이터 동기화
- `apt-analytics` 스킬: 고급 분석 지표
- `apt-trend` 스킬: 시계열 트렌드 분석
- `apt-price-collector-trade` 에이전트: 실거래가 데이터 수집
