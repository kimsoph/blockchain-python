# build-ibk_HR Skill

*버전: 1.0.0*

IBK 인사 CSV 데이터(ibk_ceo.csv, ibk_man.csv, ibk_pmt.csv)를 처리하여 `ibk_HR.db` SQLite 데이터베이스를 생성/업데이트하는 스킬.

## 트리거 조건

- 사용자가 "IBK HR DB 빌드해 줘", "인사 데이터베이스 생성", "HR DB 만들어 줘" 등의 요청을 할 때
- `/build-ibk_HR` 명령어 사용 시

## 입력/출력

| 항목 | 경로 |
|------|------|
| CSV 입력 (기본) | `3_Resources >> R-about_ibk >> sources >> csv-ibk_HR/` |
| DB 출력 (기본) | `3_Resources >> R-DB >> ibk_HR.db` |
| 아카이브 | `4_Archive >> Resources >> R-about_ibk >> ibk_HR_{기준년월}_{빌드날짜}.db` |

## 사용법

### 기본 빌드

```bash
# 기준년월 지정 (필수)
python .claude/skills/build-ibk_HR/scripts/build_hr.py build 202601

# 다른 기준년월
python .claude/skills/build-ibk_HR/scripts/build_hr.py build 202507
```

### 사용자 지정 경로

```bash
python .claude/skills/build-ibk_HR/scripts/build_hr.py build 202601 \
    --csv-dir "path/to/csv" \
    --output "path/to/output.db"
```

### 강제 재생성

```bash
python .claude/skills/build-ibk_HR/scripts/build_hr.py build 202601 --force
```

### DB 정보 조회

```bash
python .claude/skills/build-ibk_HR/scripts/build_hr.py info
```

### 데이터 검증

```bash
python .claude/skills/build-ibk_HR/scripts/build_hr.py verify
```

## DB 스키마

### HR 테이블 (33개 컬럼)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| 직번 | INTEGER | 사원번호 |
| 이름 | TEXT | 성명 |
| 성별 | TEXT | M/F |
| 직급 | INTEGER | 0~5 |
| 직위 | TEXT | 직위명 |
| 레벨 | TEXT | 임원, 부행장, 본부장, 부점장1~3, 팀장, 책임자, 행원, 기타 |
| 승진직급 | TEXT | 현재 승진 단계 |
| 직급연차 | REAL | 현 직급 연차 |
| 그룹 | TEXT | 소속 그룹 |
| 부점 | TEXT | 소속 부점 |
| 팀명 | TEXT | 소속 팀 |
| 서열 | INTEGER | 직원명부순서 |
| 랭킹 | INTEGER | 랭킹 (999999=제외) |
| 출생년월 | INTEGER | YYYYMM |
| 입행년월 | INTEGER | YYYYMM |
| 현재나이 | REAL | 기준년월 기준 |
| 입행연차 | REAL | 기준년월 기준 |
| 입행나이 | REAL | 입행 당시 나이 |
| 임피년월 | INTEGER | 만 57세 도달 년월 |
| 승진경로 | TEXT | 예: "승1←승2←승3" |
| 소요기간경로 | TEXT | 각 승진 소요기간 |
| 승진부점경로 | TEXT | 승진 당시 부점 이력 |
| 세분 | TEXT | 지점/지본/본영/본점/해외 |
| 본점여부 | INTEGER | 0/1 |
| 남성여부 | INTEGER | 0/1 |
| 인원포함여부 | INTEGER | 0/1 |
| 승진대상여부 | INTEGER | 0/1 |
| 실제생년월일 | TEXT | YYYY-MM-DD |
| 직위년월 | INTEGER | YYYYMM |
| 소속년월 | INTEGER | YYYYMM |
| 소속연차 | REAL | 현 소속 연차 |
| 오류여부 | INTEGER | 0/1 |
| 오류사유 | TEXT | 오류 상세 |

### promotion_list 테이블 (8개 컬럼)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| 직번 | INTEGER | 사원번호 |
| 이름 | TEXT | 성명 |
| 승진직급 | TEXT | 승0~승4, PCEO |
| 소요기간 | REAL | 년 단위 |
| 승진년월 | INTEGER | YYYYMM |
| 승진부점 | TEXT | 승진 당시 소속 |
| 오류여부 | INTEGER | 0/1 |
| 오류사유 | TEXT | (미사용) |

### 인덱스

- HR: 직번, 이름, 직급, 레벨, 출생년월, 입행년월
- promotion_list: 직번, 이름, 승진직급, 승진년월, 승진부점

## 핵심 비즈니스 로직

### 1. 직급→레벨 매핑

```
은행장, 전무이사, 감사, 사외이사 → 임원
집행간부 → 부행장
본부장 → 본부장
부장, 지점장, 부점장급 → 부점장 (+ 직급번호: 부점장1, 2, 3)
부부장, 부지점장, 부부점장급 → 팀장
차장, 과장 → 책임자
대리, 계장 → 행원
준정, 용역, 고경력 → 기타
```

### 2. 승진직급 서열

승진직급은 다음 순서로 상위 → 하위를 나타낸다:

```
승0 >> 승1 >> 승2 >> PCEO >> 승3 >> 승4
```

| 승진직급 | 서열 | 설명 |
|----------|------|------|
| 승0 | 1 (최상위) | 본부장급 승진 |
| 승1 | 2 | 1급 승진 |
| 승2 | 3 | 2급 승진 |
| PCEO | 4 | 부점장 후보 (Pre-CEO) |
| 승3 | 5 | 3급 승진 |
| 승4 | 6 (최하위) | 4급 승진 |

> **주의**: PCEO는 승2와 승3 사이에 위치하며, 숫자 순서와 다르므로 정렬 시 주의 필요.
> `config.py`의 `PROMOTION_ORDER` 상수 참조.

### 3. 임피년월 계산

만 57세가 되는 년월 계산:
- 1~6월 → 1월로 조정
- 7~12월 → 7월로 조정

### 4. 인원 분류

**제외 대상** (인원포함여부 = 0):
- 팀명: 기타, 노동조합, 파견
- 호칭: 고경력, 대기(순수 대기만, 대기업금융팀장 제외), 후선, 인턴

**승진대상여부** 판별:
- 기본 조건: 레벨≠기타 AND 팀명≠*기타 AND 호칭≠대기
- 승진기준년수 조건: 직급연차 >= 기준년수 (§6 참조)
- 승진직급 NULL(승진 이력 없음) + 레벨=행원: 승진대상여부 = 0
- 승진직급 '승0'(최상위): 승진대상여부 = 0

### 5. 승진 경로

직원별 승진 이력을 "승0←승1←승2" 형식으로 집계

### 6. 승진기준년수

직급기간(직급연차)이 일정 기준년수 이상인 직원만 승진대상자로 분류한다.

| 현재 직급 | 승진 대상 직급 | 기준년수 |
|-----------|---------------|---------|
| 승4 | 승3 | 9년 |
| 승3 | PCEO | 6년 |
| PCEO | 승2 | 3년 |
| 승2 | 승1 | 1년 |
| 승1 | 승0 | 0.5년 |

> 승0은 최상위 직급이므로 승진 대상 없음.
> `config.py`의 `PROMOTION_TENURE_REQUIREMENTS` 상수 참조.

판별 시점: `_merge_hr_data()`에서 employee + history 병합 후 직급연차 기반으로 재계산.

## 처리 파이프라인

```
1. 직원 데이터 처리 (ibk_man.csv)
   ├─ 컬럼명 표준화
   ├─ 날짜 변환 (출생년월, 입행년월 등)
   ├─ 나이/연차 계산
   ├─ 레벨 설정
   ├─ 부서 분류
   └─ 데이터 검증

2. 승진 데이터 처리 (ibk_pmt.csv)
   ├─ 승진 정보 파싱
   ├─ 승진 간격 계산
   └─ 승진 이력(경로) 생성

3. HR 데이터 통합
   └─ 직원 데이터 + 승진 이력 병합

4. DB 저장
   ├─ 기존 DB 아카이빙 (4_Archive/Resources/R-about_ibk/)
   ├─ HR/promotion_list 테이블 생성
   ├─ 인덱스 생성
   └─ 메타데이터 테이블 생성
```

## 폴더 구조

```
.claude/skills/build-ibk_HR/
├── SKILL.md                    # 이 파일
├── requirements.txt            # 의존성 (pandas, numpy)
└── scripts/
    ├── build_hr.py             # CLI 진입점
    ├── core/
    │   ├── __init__.py
    │   ├── config.py           # 설정 (컬럼 매핑, 레벨 체계)
    │   ├── utils.py            # 날짜/나이 계산
    │   └── validators.py       # 데이터 검증
    ├── processors/
    │   ├── __init__.py
    │   ├── employee_processor.py
    │   ├── promotion_processor.py
    │   └── ceo_processor.py
    └── db/
        ├── __init__.py
        ├── schema.py           # 스키마 정의
        └── writer.py           # DB 저장/업데이트
```

## 의존성

- pandas >= 2.0.0
- numpy >= 1.24.0

## 업데이트 로직

1. 기존 DB 존재 시 → `4_Archive/Resources/R-about_ibk/`로 아카이빙
   - 파일명 형식: `ibk_HR_{기준년월}_{빌드날짜}.db`
   - 예: `ibk_HR_202601_20260116.db`
2. 새 DB 생성 (임시 파일)
3. 검증 통과 시 원본 교체
4. DB 내부 `_metadata` 테이블에 메타데이터 저장

## 관련 리소스

- CSV 원본: `3_Resources >> R-about_ibk >> sources >> csv-ibk_HR/`
- 참조 코드: `9_Imports/ibk_HR_code_extracted/`
