# promo-query

*최종 업데이트: 2026-01-28*

IBK 승진결과 데이터를 ibk_HR.db에서 추출하여 마크다운 테이블로 출력하는 쿼리 스킬.

## 트리거 조건

- 승진 데이터 조회/추출 요청
- "승1 몇 명이야?", "직급별 승진 현황", "그룹별 승진률" 등 승진 관련 단독 질의
- promo-collector-current / promo-collector-historical 에이전트에서 호출

## 핵심 가치

1. **승진직급 서열 단일 소스**: `config.py`의 `RANK_ORDER` 1곳에서만 정의
2. **쿼리 파라미터화**: 승진년월/범위필터를 CLI 인자로 전달
3. **출력 표준화**: 마크다운 테이블 직접 출력 (sqlite3 CLI 파싱 불필요)
4. **소수집단 자동 플래그**: 5명 미만 그룹에 자동 주석
5. **입력 검증**: 승진년월 형식, 그룹명 존재 여부 사전 검증

## 사용법

```bash
python .claude/skills/promo-query/scripts/promo_query.py <command> [options]
```

### Commands (14종)

| Command | 설명 | 용도 |
|---------|------|------|
| `dates` | 승진년월 목록 조회 | 전체 회차 확인 |
| `summary` | 직급별 승진 요약 (대상자/승진자/승진률) | 현황 총괄 |
| `by-group` | 그룹별 승진 현황 | 그룹 분석 |
| `by-branch` | 부점별/세분별 분포 | 부점 분석 |
| `by-gender` | 성별 분석 (직급별) | 성별 분석 |
| `by-tenure` | 연차별 분석 (입행/직급) | 연차 분석 |
| `by-age` | 연령별 분석 (통계/분포/프로필) | 연령 분석 |
| `duration` | 소요기간 분석 | 소요기간 |
| `career-path` | 승진경로 + 본점경유 비율 | 경로 분석 |
| `career-impact` | 과거 이력 영향 (본점경험/소속연차) | 이력 영향 |
| `compare` | 승진자 vs 미승진자 프로필 비교 | 프로필 비교 |
| `cross-tab` | 교차분석 (그룹x직급, 성별x직급, ...) | 교차분석 |
| `timeline` | 시계열 추이 (최근 N회차) | 시계열 |
| `prev-compare` | 전회차/동월 YoY 비교 | 비교 분석 |

### Common Options

| Option | 설명 | 기본값 |
|--------|------|--------|
| `--date YYYYMM` | 대상 승진년월 | 최신 |
| `--scope {전행\|그룹\|부점\|세분\|본점비교}` | 분석 범위 | 전행 |
| `--filter VALUE` | 범위 필터값 (그룹명/부점명 등) | - |
| `--include-total` | 전행 평균 비교 데이터 함께 출력 | false |
| `--limit N` | TOP N 결과 | 20 |
| `--count N` | 시계열 회차 수 | 10 |
| `--format {markdown\|csv}` | 출력 형식 | markdown |
| `--db PATH` | DB 경로 (override) | 기본 경로 |

## 사용 예시

```bash
# 승진년월 목록
python .claude/skills/promo-query/scripts/promo_query.py dates

# 직급별 현황 (최신)
python .claude/skills/promo-query/scripts/promo_query.py summary

# 직급별 현황 (특정 년월)
python .claude/skills/promo-query/scripts/promo_query.py summary --date 202601

# 그룹별 현황 + 전행 평균 비교
python .claude/skills/promo-query/scripts/promo_query.py by-group --date 202601 --scope 그룹 --filter "디지털그룹" --include-total

# 시계열 추이 (최근 5회차)
python .claude/skills/promo-query/scripts/promo_query.py timeline --count 5

# 전회차/YoY 비교
python .claude/skills/promo-query/scripts/promo_query.py prev-compare --date 202601
```

## 승진직급 서열

```
승0(본부장급) >> 승1(1급) >> 승2(2급) >> PCEO(Pre-CEO) >> 승3(3급) >> 승4(4급)
```

이 서열은 `config.py`의 `RANK_ORDER`에 단 한 번만 정의되며, 모든 쿼리의 ORDER BY에 자동 적용된다.

## 승진기준년수

직급기간(직급연차)이 기준년수 이상인 직원만 승진대상자로 분류된다.

| 현재 직급 | 승진 대상 직급 | 기준년수 |
|-----------|---------------|---------|
| 승4 | 승3 | 9년 |
| 승3 | PCEO | 6년 |
| PCEO | 승2 | 3년 |
| 승2 | 승1 | 1년 |
| 승1 | 승0 | 0.5년 |

> 승진대상여부는 `build-ibk_HR` 스킬에서 DB 생성 시 직급연차 기반으로 판별된다.
> 이 스킬의 쿼리는 `승진대상여부 = 1` 필터로 이미 반영된 결과를 사용한다.
> `config.py`의 `PROMOTION_TENURE` 상수 참조.

## 디렉토리 구조

```
.claude/skills/promo-query/
├── SKILL.md
└── scripts/
    ├── promo_query.py        # CLI 진입점
    ├── core/
    │   ├── __init__.py
    │   ├── config.py         # 상수 (RANK_ORDER, DB_PATH, 필터)
    │   └── formatter.py      # 마크다운 테이블 포매터
    ├── queries/
    │   ├── __init__.py
    │   ├── current.py        # 현황 쿼리 11종
    │   └── historical.py     # 시계열 쿼리 3종 (dates, timeline, prev-compare)
    └── db/
        ├── __init__.py
        └── executor.py       # DB 연결, 쿼리 실행
```

## 의존성

- Python 3 (sqlite3 표준 라이브러리만 사용, 외부 패키지 없음)
- DB: `3_Resources/R-DB/ibk_HR.db`

## 관련 에이전트

- `promo-collector-current`: 현황 데이터 수집 시 이 스킬 호출
- `promo-collector-historical`: 시계열 데이터 수집 시 이 스킬 호출
- `promo-orchestrator`: 전체 분석 파이프라인 조율
